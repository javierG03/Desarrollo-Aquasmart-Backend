import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser, LoginRestriction, Otp
from django.utils.timezone import now, timedelta
from rest_framework.authtoken.models import Token



@pytest.mark.django_db
class TestLoginView:
    """Tests para la vista de login con restricciones"""
    
    @pytest.fixture
    def setup_user(self):
        return CustomUser.objects.create_user(
            document="123456789",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="1234567890",
            password="password123",
            is_active=True,
            is_registered=True
        )

    def test_login_success(self, setup_user):
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "password123"})
        assert response.status_code == status.HTTP_200_OK

    def test_login_invalid_credentials(self, setup_user):
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "wrongpassword"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "detail" in response.data["error"]
        assert response.data["error"]["detail"][0] == "Credenciales inválidas."


    def test_login_inactive_user(self, setup_user):
        setup_user.is_active = False
        setup_user.save()
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "password123"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "error" in response.data
        assert "detail" in response.data["error"]

    # def test_login_blocked_user(self, setup_user):
    #     LoginRestriction.objects.create(user=setup_user, attempts=5)
    #     client = APIClient()
    #     url = reverse("login")
    #     response = client.post(url, {"document": "123456789", "password": "wrongpassword"})
    
    #     assert response.status_code == status.HTTP_400_BAD_REQUEST
    #     assert "error" in response.data  # ✅ Primero verificamos que "error" existe
    #     assert "detail" in response.data["error"]  # ✅ Verificar que "detail" está dentro de "error"
    #     assert response.data["error"]["detail"][0] == "Usuario bloqueado por 30 minutos."  # ✅ Verificamos el mensaje exacto
    @pytest.mark.django_db
    def test_login_blocked_user(self, setup_user):
        restriction = LoginRestriction.objects.create(user=setup_user)

        for _ in range(5):
            restriction.register_attempt()

        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": setup_user.document, "password": "wrongpassword"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "detail" in response.data["error"]
        assert response.data["error"]["detail"][0] == "Too many failed attempts."


    @pytest.mark.django_db
    def test_login_after_unblock(self, setup_user):
        """Verifica que el usuario pueda iniciar sesión después de que pase el bloqueo."""
        restriction = LoginRestriction.objects.create(user=setup_user)

        for _ in range(5):  # Simula 5 intentos fallidos
            restriction.register_attempt()

        assert restriction.is_blocked() is True

        # Simula que han pasado 31 minutos (el bloqueo expira en 30 minutos)
        restriction.blocked_until = now() - timedelta(minutes=31)
        restriction.save()

        assert restriction.is_blocked() is False  # Ya no debería estar bloqueado


    def test_login_missing_credentials(self):
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "document" in response.data["error"]
        assert "password" in response.data["error"]



@pytest.mark.django_db
class TestAuthentication:
    """Pruebas para la autenticación de usuarios"""

    @pytest.fixture
    def setup_user(self):
        """Crea un usuario de prueba"""
        user = CustomUser.objects.create_user(
            document="123456789",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="1234567890",
            password="password123",
            is_active=True,
            is_registered=True
        )
        return user

    @pytest.fixture
    def setup_user_with_token(self, setup_user):
        """Crea un usuario con un token de autenticación"""
        token = Token.objects.create(user=setup_user)
        return setup_user, token

    def test_login_success(self, setup_user):
        """Verifica que el usuario pueda iniciar sesión correctamente"""
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "password123"})
        assert response.status_code == status.HTTP_200_OK

    def test_login_invalid_credentials(self, setup_user):
        """Verifica que el sistema rechace credenciales incorrectas"""
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "wrongpassword"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_user_not_found(self):
        """Verifica que no se pueda iniciar sesión con un documento que no existe"""
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "000000000", "password": "password123"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_login_long_document(self):
        """Verifica que no se permita un documento de más de 12 caracteres"""
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789012345", "password": "password123"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_long_password(self, setup_user):
        """Verifica que no se permita una contraseña de más de 128 caracteres"""
        client = APIClient()
        url = reverse("login")
        long_password = "a" * 129
        response = client.post(url, {"document": setup_user.document, "password": long_password})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_success(self, setup_user_with_token):
        """Verifica que un usuario autenticado pueda cerrar sesión correctamente"""
        user, token = setup_user_with_token
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        
        url = reverse("logout")
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert not Token.objects.filter(user=user).exists()

    def test_validate_otp_long_code(self, setup_user):
        """Verifica que no se permita un código OTP con más de 6 caracteres"""
        Otp.objects.create(user=setup_user, otp="123456", is_validated=False)
        client = APIClient()

        url = reverse("validate-otp")
        response = client.post(url, {"document": setup_user.document, "otp": "1234567"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_otp_user_not_found(self):
        """Verifica que no se pueda generar un OTP para un usuario que no existe"""
        client = APIClient()
        url = reverse("generate_otp_password_recovery")
        response = client.post(url, {"document": "000000000", "phone": "1234567890"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reset_password_user_not_found(self):
        """Verifica que no se pueda restablecer la contraseña con un documento que no existe"""
        client = APIClient()
        url = reverse("reset-password")
        response = client.post(url, {"document": "000000000", "new_password": "NewPassword123!"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST