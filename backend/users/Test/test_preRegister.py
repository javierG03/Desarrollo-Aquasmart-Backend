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
def test_pre_register_success(api_client):
    """✅ Un usuario debe poder pre-registrarse correctamente."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "password": "SecurePass123@",
        "address": "Calle 123",  # ✅ Agregar dirección si es obligatoria
    }

    response = api_client.post(url, data)

    print("API RESPONSE:", response.data)

    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Error inesperado: {response.data}"


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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "missing_field",
    ["document", "first_name", "last_name", "email", "phone", "password", "address"],
)
def test_pre_register_missing_fields(api_client, missing_field):
    """❌ No se debe permitir el pre-registro con datos faltantes."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "password": "SecurePass123@",
        "address": "Calle 123",  # ✅ Agregar dirección si es obligatoria
    }
    del data[missing_field]  # Eliminar un campo para simular el error

    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_field in response.data
    assert (
        response.data[missing_field][0].code == "required"
    ), f"Mensaje inesperado: {response.data[missing_field][0]}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_email", ["plainaddress", "user@com", "user@.com", "user@domain..com"]
)
def test_pre_register_invalid_email(api_client, invalid_email):
    """❌ No se debe permitir el pre-registro con emails inválidos."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": invalid_email,
        "phone": "1234567890",
        "password": "SecurePass123@",
        "address": "Calle 123",
    }
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
    assert response.data["email"][0].code == "invalid"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_phone", ["", "abcd1234", "1234567890" * 50, "@1234567890"]
)
def test_pre_register_invalid_phone(api_client, invalid_phone):
    """❌ No se debe permitir el pre-registro con un teléfono inválido."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": invalid_phone,
        "password": "SecurePass123@",
        "address": "Calle 123",
    }
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    print("API RESPONSE:", response.data)
    assert (
        "phone" in response.data
    ), f"Clave inesperada en la respuesta: {response.data.keys()}"
