import pytest
from django.urls import reverse
from rest_framework import status
from users.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.mark.django_db
class TestLoginView:
    """ Pruebas para la vista de inicio de sesión """

    def setup_method(self):
        """ Configuración inicial: Crear un usuario de prueba """
        self.user = CustomUser.objects.create_user(
            document="123456789",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="1234567890",
            password="password123",
            is_active=True  # Usuario activo
        )
        self.url = reverse("login")  # Asegúrate de que la URL de login está correctamente definida en urls.py

    def test_login_exitoso(self, client):
        """ Prueba de inicio de sesión exitoso """
        response = client.post(self.url, {"document": "123456789", "password": "password123"})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_usuario_no_existe(self, client):
        """ Prueba cuando el usuario no existe """
        response = client.post(self.url, {"document": "000000000", "password": "password123"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Not found."

    def test_contraseña_incorrecta(self, client):
        """ Prueba con una contraseña incorrecta """
        response = client.post(self.url, {"document": "123456789", "password": "wrongpassword"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Invalid credentials."

    def test_usuario_inactivo(self, client):
        """ Prueba cuando el usuario está inactivo """
        self.user.is_active = False
        self.user.save()

        response = client.post(self.url, {"document": "123456789", "password": "password123"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Your account is inactive. Please contact support."

    def test_sin_credenciales(self, client):
        """ Prueba cuando no se envían credenciales """
        response = client.post(self.url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Username and password are required."
