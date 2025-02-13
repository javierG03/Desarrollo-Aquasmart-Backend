from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import CustomUser
from .serializers import  RecoverPasswordSerializer, ValidateOtpSerializer, ResetPasswordSerializer
from .doc_serializers import LoginSerializer, LoginResponseSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]
    """
    Vista para el inicio de sesión de usuarios.

    Permite a los usuarios autenticarse mediante su documento y contraseña.
    Si las credenciales son correctas y el usuario está activo, se devuelve un token de acceso.

    Métodos:
        - `post(request)`: Autentica al usuario y devuelve un token JWT.
        - `get_permissions()`: Define permisos para la vista.
    """

    @extend_schema(
        summary="Inicio de sesión",
        description="Autentica un usuario con su documento y contraseña, y devuelve un token de acceso.",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: {"description": "Campos requeridos", "example": {"detail": "Username and password are required."}},
            403: {"description": "Usuario inactivo", "example": {"detail": "Your account is inactive. Please contact support."}},
            401: {"description": "Credenciales incorrectas", "example": {"detail": "Invalid credentials."}},
            404: {"description": "Usuario no encontrado", "example": {"detail": "Not found."}},
        },
        examples=[
            OpenApiExample(
                "Ejemplo de solicitud",
                value={"document": "123456789", "password": "mypassword"},
                request_only=True
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        """
        Maneja la autenticación de usuarios.

        Parámetros:
            - `document` (str): Número de documento del usuario.
            - `password` (str): Contraseña del usuario.

        Respuestas:
            - 200: Retorna los tokens de acceso y refresco si las credenciales son correctas.
            - 400: Faltan el documento o la contraseña en la solicitud.
            - 403: La cuenta del usuario está inactiva.
            - 401: Credenciales incorrectas.
            - 404: Usuario no encontrado.
        """
        document = request.data.get('document')
        password = request.data.get('password')

        if not document or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(document=document)

            # Verificar si el usuario está activo
            if not user.is_active:
                return Response({"detail": "Your account is inactive. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

            # Validar la contraseña
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                user.last_login = timezone.now()
                user.save()
                user_logged_in.send(sender=user.__class__, request=request, user=user)

                return Response({
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        except CustomUser.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

   


class RecoverPasswordView(APIView):
    permission_classes = [AllowAny]
    """
    Vista para la recuperación de contraseña mediante OTP.

    Permite a los usuarios solicitar un código OTP que se enviará por SMS o correo electrónico.
    Este código podrá ser utilizado para restablecer la contraseña.

    Métodos:
        - `post(request)`: Genera y envía un código OTP.
        - `get_permissions()`: Define permisos para la vista.
    """

    @extend_schema(
        summary="Recuperar contraseña",
        description="Se enviará un código OTP por SMS o correo para recuperar la contraseña.",
        request=RecoverPasswordSerializer,
        responses={
            200: {"description": "Correo enviado correctamente", "example": {"detail": "OTP enviado."}},
            400: {"description": "Error en la solicitud", "example": {"document": ["Este campo es obligatorio."]}},
        }
    )
    def post(self, request):
        """
        Maneja la solicitud de recuperación de contraseña.

        Parámetros:
            - `document` (str): Número de documento del usuario.

        Respuestas:
            - 200: Se ha enviado el OTP correctamente al correo registrado.
            - 400: Error en la solicitud, por ejemplo, si falta el documento en la petición.
        """
        serializer = RecoverPasswordSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

  

class ValidateOtpView(APIView):
    permission_classes = [AllowAny]
    """
    Vista para validar un código OTP.

    Permite a los usuarios enviar un OTP asociado a su documento para verificar su identidad.
    No requiere autenticación para el método `POST`.

    Métodos:
    - `POST`: Recibe un `document` y un `otp` para validarlo.
    """

    @extend_schema(
        request=ValidateOtpSerializer,
        responses={
            200: {"message": "OTP validado correctamente.","example": {"message": "OTP validado correctamente."}},
            400: {"message": "Errores de validación."}
        },
        description="Valida un OTP asociado a un documento.",
        summary="Validar OTP",
    )
    def post(self, request):
        """
        Procesa la validación de un OTP.

        Recibe un documento y un OTP en el cuerpo de la solicitud. Si el OTP es válido,
        devuelve un mensaje de éxito; de lo contrario, devuelve errores de validación.

        Parámetros:
        - `request.data` (dict): Debe contener `document` y `otp`.

        Retorno:
        - `200 OK`: Si el OTP es válido.
        - `400 BAD REQUEST`: Si hay errores en la validación.
        """
        serializer = ValidateOtpSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "OTP validado correctamente."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    """
    Vista para restablecer la contraseña de un usuario.

    Permite a los usuarios restablecer su contraseña proporcionando su documento 
    y habiendo validado un OTP previamente. No requiere autenticación para `POST`.

    Métodos:
    - `POST`: Recibe un `document` y una `new_password` para cambiar la contraseña.
    """

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={
            200: {"message": "Contraseña restablecida correctamente."},
            400: {"message": "Errores de validación."}
        },
        description="Restablece la contraseña de un usuario si ha validado un OTP.",
        summary="Restablecer contraseña",
    )
    def post(self, request):
        """
        Procesa el restablecimiento de la contraseña.

        Recibe un documento y una nueva contraseña en el cuerpo de la solicitud. 
        Si el OTP fue validado previamente, la contraseña se actualiza.

        Parámetros:
        - `request.data` (dict): Debe contener `document` y `new_password`.

        Retorno:
        - `200 OK`: Si la contraseña fue cambiada con éxito.
        - `400 BAD REQUEST`: Si hay errores en la validación.
        """
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Contraseña restablecida correctamente."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    