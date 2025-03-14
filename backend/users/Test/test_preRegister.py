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
    "weak_password", ["123456", "password", "SecurePass", "abc123"]
)
def test_pre_register_weak_password(api_client, weak_password):
    """❌ No se debe permitir el pre-registro con contraseñas débiles."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "password": weak_password,
        "address": "Calle 123",
    }
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data

    password_errors = response.data["password"]

    # ✅ Maneja el caso de diccionario con "detail" y el caso de lista de errores
    if isinstance(password_errors, dict) and "detail" in password_errors:
        error_message = " ".join([str(err) for err in password_errors["detail"]])
    else:
        error_message = " ".join([str(err) for err in password_errors])

    assert (
        "contraseña" in error_message.lower()
    ), f"Mensaje inesperado: {error_message}"



@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_document", ["", "123", "12345678901234567890", "abc123!", "@invalid"]
)
def test_pre_register_invalid_document(api_client, invalid_document):
    """❌ No se debe permitir el pre-registro con un documento inválido."""
    url = reverse("customuser-pre-register")
    data = {
        "document": invalid_document,
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "password": "SecurePass123@",
        "address": "Calle 123",
    }

    response = api_client.post(url, data)

    print("API RESPONSE:", response.data)
    print("API STATUS CODE:", response.status_code)

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La API aceptó un documento inválido ({invalid_document}) con status {response.status_code}.\n"
        f"Respuesta de la API: {response.data}"
    )

    assert (
        "document" in response.data
    ), f"Clave inesperada en la respuesta: {response.data.keys()}"



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

@pytest.mark.django_db
@pytest.mark.parametrize(
    "weak_password", ["Secure123", "onlylowercase", "ONLYUPPERCASE", "1234567890", ""]
)
def test_pre_register_weak_password_constraints(api_client, weak_password):
    """❌ No se debe permitir el pre-registro con contraseñas sin caracteres especiales o sin letras."""
    url = reverse("customuser-pre-register")
    data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "password": weak_password,
        "address": "Calle 123",
    }
    response = api_client.post(url, data)

    print("API RESPONSE:", response.data)
    print("API STATUS CODE:", response.status_code)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data

    password_errors = response.data["password"]

    # ✅ Maneja ambos casos: lista de errores o diccionario con "detail"
    if isinstance(password_errors, dict) and "detail" in password_errors:
        error_message = " ".join([str(err) for err in password_errors["detail"]])
    else:
        error_message = " ".join([str(err) for err in password_errors])

    if weak_password == "":  # Caso especial para contraseña vacía
        assert error_message.lower() == "this field may not be blank.", f"Mensaje inesperado: {error_message}"
    else:
        assert "contraseña" in error_message.lower(), f"Mensaje inesperado: {error_message}"








