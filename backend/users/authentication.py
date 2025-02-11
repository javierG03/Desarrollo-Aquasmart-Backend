from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import CustomUser
from .serializers import  RecuperarContraseñaSerializer
from .doc_serializers import LoginSerializer, LoginResponseSerializer

class LoginView(APIView):
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

    def get_permissions(self):
        """
        Define los permisos de la vista.

        Para el método POST, no se requiere autenticación.
        """
        if self.request.method == 'POST':
            return []
        return super().get_permissions()


class RecuperarContraseñaView(APIView):
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
        request=RecuperarContraseñaSerializer,
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
        serializer = RecuperarContraseñaSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """
        Define los permisos de la vista.

        Para el método POST, no se requiere autenticación.
        """
        if self.request.method == 'POST':
            return []
        return super().get_permissions()
