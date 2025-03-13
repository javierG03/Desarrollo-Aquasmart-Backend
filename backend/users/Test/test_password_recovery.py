import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser, Otp
from django.utils.timezone import now, timedelta


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    """Usuario registrado y activo"""
    return CustomUser.objects.create_user(
        document="123456789012",
        first_name="John",
        last_name="Doe",
        email="johndoe@example.com",
        phone="1234567890",
        password="SecurePass123",
        is_active=True,
        is_registered=True,
    )


@pytest.fixture
def inactive_user(db):
    """Usuario inactivo"""
    return CustomUser.objects.create_user(
        document="111111111111",
        first_name="Inactive",
        last_name="User",
        email="inactive@example.com",
        phone="5555555555",
        password="InactivePass123",
        is_active=False,
        is_registered=True,
    )

@pytest.fixture
def auth_token(api_client, test_user):
    """Obtiene un token de autenticación válido para el usuario de prueba"""
    url = reverse("validate-tokenr")  # Ajustar según el endpoint real
    data = {"document": test_user.document, "password": "SecurePass123"}
    response = api_client.post(url, data)
    
    assert response.status_code == 200, f"Error al obtener token: {response.data}"
    return response.data["access"]  # O "token" según el formato de la API


@pytest.fixture
def otp_for_user(db, test_user):
    """Genera un OTP ya validado para el usuario"""
    otp = Otp.objects.create(user=test_user, otp="123456", is_validated=True)
    return otp



@pytest.fixture
def expired_otp(db, test_user):
    """Simula un OTP caducado sin modificar el modelo."""
    otp = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    
    # Simula que la API verifica si el OTP ha expirado
    def mock_is_expired():
        return True  # Forzamos que el OTP se considere caducado
    
    # Reemplazar método en el test
    otp.is_expired = mock_is_expired
    return otp


@pytest.fixture
def used_otp(db, test_user):
    """Genera un OTP ya utilizado"""
    return Otp.objects.create(user=test_user, otp="111111", is_validated=True)


@pytest.mark.django_db
def test_request_password_recovery(api_client, test_user):
    """✅ Usuario registrado solicita recuperación de contraseña correctamente."""
    url = reverse("generate_otp_password_recovery")
    data = {"document": test_user.document, "phone": test_user.phone}  # 📌 Agregar 'phone'
    
    response = api_client.post(url, data)
    
    assert response.status_code == status.HTTP_200_OK, f"Error en respuesta: {response.data}"
    assert "Se ha enviado el código de recuperación" in response.data["message"]





@pytest.mark.django_db
@pytest.mark.parametrize("invalid_document", ["", "123", "abc123!", "12345678901234567890"])
def test_request_password_recovery_invalid_document(api_client, auth_token, invalid_document):
    """❌ No se puede solicitar recuperación con documento inválido."""
    url = reverse("recover-password")
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {"document": invalid_document}
    
    response = api_client.post(url, data, headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_message = response.data.get("error", {}).get("detail", response.data.get("detail"))
    assert error_message is not None, f"Error esperado pero no encontrado en: {response.data}"


@pytest.mark.django_db
def test_request_password_recovery_unregistered_user(api_client, auth_token):
    """❌ Solicitud de recuperación con usuario no registrado"""
    url = reverse("change-password")
    data = {"document": "999999999999"}
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = api_client.post(url, data, headers=headers)

    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED], f"Error inesperado: {response.data}"



@pytest.mark.django_db
def test_request_password_recovery_inactive_user(api_client, inactive_user):
    """❌ Solicitud de recuperación con usuario inactivo"""
    url = reverse("change-password")
    data = {"document": inactive_user.document}
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Su cuenta está inactiva" in response.data["error"]["detail"]

@pytest.mark.django_db
def test_reset_password_with_valid_otp(api_client, test_user, otp_for_user):
    """✅ OTP válido permite resetear contraseña"""
    
    # Validar el OTP antes de restablecer la contraseña
    validate_otp_url = reverse("validate-otp")
    api_client.post(validate_otp_url, {"document": test_user.document, "otp": otp_for_user.otp})

    url = reverse("reset-password")
    data = {
        "document": test_user.document,
        "otp": otp_for_user.otp,
        "new_password": "NewSecurePass123@"
    }
    response = api_client.post(url, data)

    print("\nAPI RESPONSE:", response.data)  # 🔍 Verificar respuesta real

    assert response.status_code == status.HTTP_200_OK, f"Error inesperado: {response.data}"




@pytest.mark.django_db
@pytest.mark.parametrize("invalid_otp", ["ABC123", "12@34!", "12345"])
def test_reset_password_with_invalid_otp(api_client, test_user, otp_for_user, auth_token, invalid_otp):
    """❌ OTP con formato inválido no debe ser aceptado."""
    url = reverse("reset-password")
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {"document": test_user.document, "otp": invalid_otp, "new_password": "NewSecurePass123!"}
    
    response = api_client.post(url, data, headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_message = response.data.get("detail", [""])[0]
    assert "OTP inválido" in error_message, f"Mensaje inesperado: {error_message}"



@pytest.mark.django_db
def test_reset_password_with_expired_otp(api_client, test_user, auth_token):
    """❌ OTP expirado no debe ser aceptado."""
    url = reverse("reset-password")
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Simulamos que el OTP ha expirado
    expired_otp = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    expired_otp.is_expired = lambda: True  # Simulación de expiración
    
    data = {"document": test_user.document, "otp": "654321", "new_password": "NewSecurePass123!"}
    response = api_client.post(url, data, headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_message = response.data.get("detail", [""])[0]
    assert "OTP ha caducado" in error_message, f"Mensaje inesperado: {error_message}"



@pytest.mark.django_db
def test_reset_password_with_used_otp(api_client, test_user, used_otp):
    """❌ OTP ya utilizado no permite resetear contraseña"""
    url = reverse("reset-password")
    data = {
        "document": test_user.document,
        "otp": used_otp.otp,  # OTP ya usado
        "new_password": "NewSecurePass123@"
    }

    response = api_client.post(url, data)

    print("\nAPI RESPONSE:", response.data)  # 👀 Verificar respuesta real

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "ya ha sido utilizado" in response.data.get("detail", ""), f"Mensaje inesperado: {response.data}"



@pytest.mark.django_db
@pytest.mark.parametrize("weak_password", ["123456", "password", "SecurePass"])
def test_reset_password_with_weak_password(api_client, test_user, otp_for_user, weak_password):
    """❌ Nueva contraseña sin requisitos mínimos debe ser rechazada."""

    url = reverse("reset-password")
    data = {
        "document": test_user.document,
        "otp": otp_for_user.otp,
        "new_password": weak_password
    }
    response = api_client.post(url, data)

    print("\nAPI RESPONSE:", response.data)  # 🔍 Verificar respuesta real

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # 🔧 Extraer correctamente los errores
    error_messages = response.data.get("detail", [])  # Lista de errores
    error_messages = " ".join([str(msg) for msg in error_messages])  # Convertir a string

    assert "contraseña" in error_messages.lower(), f"Mensaje inesperado: {error_messages}"



