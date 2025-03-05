import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser, LoginRestriction

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
        assert response.data["detail"] == "Your account is inactive. Please contact support."

    def test_login_blocked_user(self, setup_user):
        LoginRestriction.objects.create(user=setup_user, attempts=5)
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {"document": "123456789", "password": "wrongpassword"})
    
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data  # ✅ Primero verificamos que "error" existe
        assert "detail" in response.data["error"]  # ✅ Verificar que "detail" está dentro de "error"
        assert response.data["error"]["detail"][0] == "Usuario bloqueado por 30 minutos."  # ✅ Verificamos el mensaje exacto


    def test_login_missing_credentials(self):
        client = APIClient()
        url = reverse("login")
        response = client.post(url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "document" in response.data
        assert "password" in response.data
