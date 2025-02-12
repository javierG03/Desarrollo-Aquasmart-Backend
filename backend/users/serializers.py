from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .models import DocumentType, PersonType, CustomUser, LoginHistory, Otp
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password

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
    document = serializers.CharField(max_length=12)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        document = data.get('document')
        otp = data.get('otp')

        # Verificar si el usuario existe
        try:
            user = CustomUser.objects.get(document=document)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado con este documento.")

        # Verificar si el OTP es válido
        try:
            otp_instance = Otp.objects.get(user=user, otp=otp, is_validated=False)
        except Otp.DoesNotExist:
            raise serializers.ValidationError("OTP inválido o ya ha sido utilizado.")

        # Verificar si el OTP no ha expirado
        if not otp_instance.validateOTP():
            raise serializers.ValidationError("El OTP ha expirado.")

        # Marcar el OTP como validado
        otp_instance.is_validated = True
        otp_instance.save()

        return data     

class ResetPasswordSerializer(serializers.Serializer):
    document = serializers.CharField(max_length=12)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        document = data.get('document')
        new_password = data.get('new_password')

        # Verificar si el usuario existe
        try:
            user = CustomUser.objects.get(document=document)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"document": "Usuario no encontrado con este documento."})

        # Verificar si existe un OTP validado para este usuario
        try:
            otp_instance = Otp.objects.get(user=user, is_validated=True)
        except Otp.DoesNotExist:
            raise serializers.ValidationError({"otp": "No hay un OTP validado para este usuario."})

        # Validar que la nueva contraseña no sea la misma que la actual
        if check_password(new_password, user.password):
            raise serializers.ValidationError({"new_password": "No puedes usar la misma contraseña actual."})

        # Validar la contraseña con las reglas de Django
        try:
            validate_password(new_password, user=user)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        return data

    def save(self):
        """Actualiza la contraseña del usuario y elimina el OTP validado."""
        document = self.validated_data['document']
        new_password = self.validated_data['new_password']

        user = CustomUser.objects.get(document=document)
        user.password = make_password(new_password)  # Encripta la nueva contraseña
        user.save()

        # Eliminar todos los OTP validados del usuario
        Otp.objects.filter(user=user, is_validated=True).delete()

        return user