import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser, PersonType


@pytest.fixture
def api_client():
    """Cliente API para realizar las solicitudes de prueba."""
    return APIClient()


@pytest.fixture
def person_type(db):
    """Crea y guarda un tipo de persona válido en la base de datos."""
    return PersonType.objects.create(typeName="Natural")


@pytest.mark.django_db
def test_user_pre_register(api_client, person_type):
    """✅ Verifica que la API reciba correctamente los datos del pre-registro."""

    # 🔹 URL del pre-registro
    pre_register_url = reverse("customuser-pre-register")

    # 🔹 Datos del usuario a registrar
    user_data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "address": "123 Main St.",
        "password": "SecurePass123.",
        "person_type": person_type.pk,  # ID del tipo de persona creado en el fixture
    }

    # 🔹 Enviar la solicitud de pre-registro
    response = api_client.post(pre_register_url, user_data, format="json")

    print("🔹 API RESPONSE:", response.data)  # Depuración

    # ✅ Verificar la respuesta de la API
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Error en pre-registro: {response.data}"
    assert "message" in response.data, "❌ No se recibió un mensaje de confirmación."
    assert response.data["message"] == "Usuario Pre-registrado exitosamente."

    # ✅ Verificar que el usuario se creó en la base de datos
    assert CustomUser.objects.filter(
        document="123456789012"
    ).exists(), "❌ El usuario no fue creado en la base de datos."


@pytest.mark.django_db
def test_user_pre_register_valid_data(api_client, person_type):
    """✅ Un usuario puede pre-registrarse correctamente con datos válidos."""

    pre_register_url = reverse("customuser-pre-register")
    user_data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "address": "123 Main St.",
        "password": "SecurePass123.",
        "person_type": person_type.pk,
    }

    response = api_client.post(pre_register_url, user_data, format="json")

    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Error en pre-registro: {response.data}"
    assert response.data["message"] == "Usuario Pre-registrado exitosamente."
    assert CustomUser.objects.filter(document="123456789012").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "missing_field",
    [
        "document",
        "first_name",
        "last_name",
        "email",
        "phone",
        "password",
    ],
)
def test_user_pre_register_missing_required_fields(api_client, missing_field):
    """❌ El pre-registro debe fallar si falta un campo obligatorio."""

    pre_register_url = reverse("customuser-pre-register")
    user_data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "address": "123 Main St.",
        "password": "SecurePass123.",
    }

    del user_data[missing_field]  # Eliminar el campo obligatorio para la prueba

    response = api_client.post(pre_register_url, user_data, format="json")

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"El sistema aceptó un registro inválido: {response.data}"
    assert (
        missing_field in response.data
    ), f"❌ No se detectó la falta de {missing_field} en la respuesta."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_email",
    [
        "correo-invalido",
        "user@.com",
        "user@domain",
        "user@domain,com",
        "user@domain..com",
    ],
)
def test_user_pre_register_invalid_email(api_client, person_type, invalid_email):
    """❌ No se debe permitir el pre-registro con un email inválido."""

    pre_register_url = reverse("customuser-pre-register")
    user_data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": invalid_email,
        "phone": "1234567890",
        "address": "123 Main St.",
        "password": "SecurePass123.",
        "person_type": person_type.pk,
    }

    response = api_client.post(pre_register_url, user_data, format="json")

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"❌ Se permitió un email inválido: {response.data}"
    assert (
        "email" in response.data
    ), "❌ No se recibió un mensaje de error sobre el email inválido."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "weak_password",
    ["123456", "password", "abc123", "john123", "123456789"],
)
def test_user_pre_register_weak_password(api_client, person_type, weak_password):
    """❌ No se debe permitir el pre-registro con una contraseña débil."""

    pre_register_url = reverse("customuser-pre-register")
    user_data = {
        "document": "123456789012",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone": "1234567890",
        "address": "123 Main St.",
        "password": weak_password,
        "person_type": person_type.pk,
    }

    response = api_client.post(pre_register_url, user_data, format="json")

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), f"❌ Se permitió una contraseña débil: {response.data}"
    assert (
        "password" in response.data
    ), "❌ No se recibió un mensaje de error sobre la contraseña débil."
