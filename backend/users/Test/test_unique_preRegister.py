import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser


@pytest.fixture
def api_client():
    """Cliente API para realizar las solicitudes de prueba."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Usuario de prueba ya registrado en la base de datos."""
    return CustomUser.objects.create_user(
        document="123456789012",
        first_name="John",
        last_name="Doe",
        email="johndoe@example.com",
        phone="1234567890",
        password="SecurePass123@",
        is_active=True,
        is_registered=True,
    )


@pytest.mark.django_db
def test_pre_register_existing_document(api_client, test_user):
    """❌ No se debe permitir el pre-registro con un documento ya registrado."""
    url = reverse("customuser-pre-register")
    data = {
        "document": test_user.document,
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "janesmith@example.com",
        "phone": "9876543210",
        "password": "AnotherPass123@",
        "address": "Calle 123",  # ✅ Agregar dirección si es obligatoria
    }
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "document" in response.data
    assert "El usuario ya pasó el pre-registro." in response.data["document"][0]


@pytest.mark.django_db
def test_pre_register_existing_email(api_client, test_user):
    """❌ No se debe permitir el pre-registro con un email ya registrado."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "999999999999",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": test_user.email,
        "phone": "9876543210",
        "password": "AnotherPass123@",
        "address": "Calle 123",  # ✅ Agregar dirección si es obligatoria
    }
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
    assert "ya está registrado" in response.data["email"][0]
