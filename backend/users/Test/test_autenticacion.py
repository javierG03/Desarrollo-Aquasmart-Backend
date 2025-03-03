import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser

@pytest.mark.django_db
class TestLoginView:
    """Tests for the LoginView"""

    def setup_method(self):
        """Setup a test user"""
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            document="123456789",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="1234567890",
            password="password123",
            is_active=True,
            is_registered=True
        )
        self.url = reverse("login")  # Ensure this URL name matches your URL configuration

    def test_login_success(self):
        """Test successful login"""
        response = self.client.post(self.url, {"document": "01234", "password": "contraseña123"})
        print(response.data)  # 👀 Verifica qué error está devolviendo el endpoint
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data


    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(self.url, {"document": "01234", "password": "wrongpassword"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Invalid credentials."
        print(response.data)  # Para ver qué está fallando

    def test_login_inactive_user(self):
        """Test login with an inactive user"""
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {"document": "012345", "password": "contraseña123"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Your account is inactive. Please contact support."
        print(response.data)  # Para ver qué está fallando

    def test_login_missing_credentials(self):
        """Test login with missing credentials"""
        response = self.client.post(self.url, {})
        print(response.data)  # 👀 Revisa la estructura del error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "document" in response.data
        assert "password" in response.data

