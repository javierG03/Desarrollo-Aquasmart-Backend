from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .models import DocumentType, PersonType, CustomUser, LoginHistory, Otp
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import NotFound
from .validate import validate_user,validate_otp
class DocumentTypeSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo DocumentType.
    Representa los tipos de documentos disponibles.
    """
    class Meta:
        model = DocumentType
        fields = ['documentTypeId', 'typeName']

class PersonTypeSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PersonType.
    Representa los tipos de personas en el sistema.
    """
    class Meta:
        model = PersonType
        fields = ['personTypeId', 'typeName']

class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo CustomUser.
    Gestiona la creación de usuarios, incluyendo el manejo seguro de contraseñas.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    document_type = serializers.PrimaryKeyRelatedField(queryset=DocumentType.objects.all(), required=False)
    person_type = serializers.PrimaryKeyRelatedField(queryset=PersonType.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = [
            'document', 'first_name', 'last_name', 'email', 
            'document_type', 'person_type', 'phone', 'address',
            'password','isRegistered', 'is_active',
        ]
        read_only_fields = ('isRegistered', 'is_active')       

    def create(self, validated_data):
        """
        Crea un usuario nuevo con la contraseña hasheada y lo deja inactivo por defecto.
        """
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['is_active'] = False
        user = CustomUser.objects.create(**validated_data)
        user.save()
        return user

class LoginHistorySerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo LoginHistory.
    Almacena los registros de inicio de sesión de los usuarios.
    """
    class Meta:
        model = LoginHistory
        fields = ['timestamp', 'user']  

class RecoverPasswordSerializer(serializers.Serializer):
    """
    Serializer para la recuperación de contraseña mediante OTP.
    Recibe el documento del usuario y envía un OTP al correo registrado.
    """
    document = serializers.CharField(max_length=12)  

    def validate_document(self, value):
        """
        Verifica si el usuario con el documento proporcionado existe.
        """
        user = get_object_or_404(CustomUser, document=value)
        return user
    
    def create(self, validated_data):
        """
        Genera un nuevo OTP para la recuperación de contraseña y lo envía por correo.
        """
        user = validated_data['document']  
        
        # Elimina OTPs previos y genera uno nuevo
        Otp.objects.filter(user=user).delete()
        nuevo_otp = Otp.objects.create(user=user)
        otp_generado = nuevo_otp.generateOTP()
        
        #Prueba de envia (desarollo para el menaje llegue a la cosnsola)
        try:
            self.send_email_recover(user.email, otp_generado)
        except Exception as e:
            raise serializers.ValidationError(f"Error al enviar el correo: {str(e)}")

        return {'otp': otp_generado, 'message': 'Se ha enviado un correo con el OTP para recuperar la contraseña.'}

    def send_email_recover(self, email, token):
        """
        Envía un correo con el OTP de recuperación de contraseña.
        """
        asunto = "Recuperación de Contraseña"
        mensaje = f"Su OTP de recuperación es: {token}. Úselo para restablecer su contraseña."
        remitente = "noreply@example.com"
        send_mail(asunto, mensaje, remitente, [email])

class ValidateOtpSerializer(serializers.Serializer):
    """
    Serializador para la validación de OTP (One-Time Password).

    Este serializador permite verificar un OTP ingresado por el usuario para autenticación o 
    verificación de identidad. El OTP debe ser válido, no estar expirado y no haber sido utilizado previamente.

    Campos:
    - `document` (str): Documento de identidad del usuario.
    - `otp` (str): Código OTP de 6 dígitos enviado al usuario.

    Validaciones:
    - Verifica que el usuario exista.
    - Comprueba que el OTP es válido y no ha sido utilizado.
    - Verifica que el OTP no haya expirado.
    - Si la validación es exitosa, marca el OTP como validado.

    Excepciones:
    - `NotFound`: Si el usuario no existe.
    - `ValidationError`: Si el OTP es incorrecto o ya ha sido utilizado.
    - `serializers.ValidationError`: Si el OTP ha expirado.
    """

    document = serializers.CharField(max_length=12)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        """
        Valida el OTP y la existencia del usuario.

        Pasos de validación:
        1. Verifica si existe un usuario con el documento proporcionado.
        2. Comprueba que el OTP ingresado sea correcto y no haya sido utilizado.
        3. Verifica que el OTP no haya expirado.
        4. Si el OTP es válido, lo marca como validado y lo guarda.

        Parámetros:
        - `data` (dict): Contiene `document` y `otp`.

        Retorno:
        - `data` (dict): Devuelve los mismos datos si la validación es exitosa.

        Excepciones:
        - `NotFound`: Si el usuario no existe.
        - `ValidationError`: Si el OTP es incorrecto o ya ha sido utilizado.
        - `serializers.ValidationError`: Si el OTP ha expirado.
        """
        document = data.get("document")
        otp = data.get("otp")

        # Verificar si el usuario existe
        user = validate_user(document)

        # Verificar si el OTP es válido y no ha sido utilizado
        otp_instance = validate_otp(user=user, is_validated=False, otp=otp)

        # Verificar si el OTP ha expirado
        if not otp_instance.validateOTP():
            raise serializers.ValidationError({"detail": "El OTP ha expirado."})

        # Marcar el OTP como validado
        otp_instance.is_validated = True
        otp_instance.save()

        return data

class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializador para restablecer la contraseña de un usuario.

    Este serializador permite a un usuario cambiar su contraseña después de validar su identidad
    mediante un OTP previamente verificado.

    Campos:
    - `document` (str): Documento de identidad del usuario.
    - `new_password` (str, write_only): Nueva contraseña a establecer.

    Validaciones:
    - Verifica que el usuario exista.
    - Comprueba que el usuario tenga un OTP validado.
    - No permite reutilizar la contraseña actual.
    - Valida la nueva contraseña según las reglas de seguridad de Django.

    Acciones al guardar:
    - Actualiza la contraseña del usuario.
    - Elimina todos los OTP validados del usuario.
    """

    document = serializers.CharField(max_length=12)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Valida la nueva contraseña y verifica la existencia del usuario y su OTP validado.

        Pasos de validación:
        1. Verifica si existe un usuario con el documento proporcionado.
        2. Comprueba si hay un OTP validado asociado al usuario.
        3. Asegura que la nueva contraseña no sea idéntica a la actual.
        4. Valida la nueva contraseña según las reglas de seguridad de Django.

        Parámetros:
        - `data` (dict): Contiene `document` y `new_password`.

        Retorno:
        - `data` (dict): Devuelve los mismos datos si la validación es exitosa.

        Excepciones:
        - `NotFound`: Si el usuario no existe.
        - `ValidationError`: Si no hay un OTP validado para el usuario.
        - `serializers.ValidationError`: Si la nueva contraseña es igual a la actual.
        - `serializers.ValidationError`: Si la nueva contraseña no cumple con las reglas de Django.
        """
        document = data.get("document")
        new_password = data.get("new_password")

        # Verificar si el usuario existe
        user = validate_user(document)

        # Verificar si existe un OTP validado para este usuario
        otp_instance = validate_otp(user=user, is_validated=True)

        # Validar que la nueva contraseña no sea la misma que la actual
        if check_password(new_password, user.password):
            raise serializers.ValidationError({"detail": "No puedes usar la misma contraseña actual."})

        # Validar la contraseña con las reglas de Django
        try:
            validate_password(new_password, user=user)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"detail": e.messages})

        return data

    def save(self):
        """
        Guarda la nueva contraseña del usuario y elimina los OTP validados.

        Acciones:
        1. Encripta la nueva contraseña y la asigna al usuario.
        2. Guarda los cambios en la base de datos.
        3. Elimina todos los OTP validados del usuario para mayor seguridad.

        Retorno:
        - `CustomUser`: Instancia del usuario con la nueva contraseña guardada.
        """
        document = self.validated_data['document']
        new_password = self.validated_data['new_password']

        user = CustomUser.objects.get(document=document)
        user.password = make_password(new_password)  # Encripta la nueva contraseña
        user.save()

        # Eliminar todos los OTP validados del usuario
        Otp.objects.filter(user=user, is_validated=True).delete()

        return user