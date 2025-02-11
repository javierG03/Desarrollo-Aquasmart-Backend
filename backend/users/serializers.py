from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .models import DocumentType, PersonType, CustomUser, LoginHistory, Otp

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

class RecuperarContraseñaSerializer(serializers.Serializer):
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
            self.enviar_correo_recuperacion(user.email, otp_generado)
        except Exception as e:
            raise serializers.ValidationError(f"Error al enviar el correo: {str(e)}")

        return {'otp': otp_generado, 'message': 'Se ha enviado un correo con el OTP para recuperar la contraseña.'}

    def enviar_correo_recuperacion(self, email, token):
        """
        Envía un correo con el OTP de recuperación de contraseña.
        """
        asunto = "Recuperación de Contraseña"
        mensaje = f"Su OTP de recuperación es: {token}. Úselo para restablecer su contraseña."
        remitente = "noreply@example.com"
        send_mail(asunto, mensaje, remitente, [email])