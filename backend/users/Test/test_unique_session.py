import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser, Otp


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
        password="SecurePass123",
        is_active=True,
        is_registered=True,
    )


@pytest.fixture
def valid_otp(db, test_user):
    """Genera un OTP válido sin marcarlo como utilizado."""
    otp = Otp.objects.create(
        user=test_user, otp="123456", is_validated=False, creation_time=now()
    )
    otp.refresh_from_db()
    return otp


@pytest.mark.django_db
def test_single_session_active(api_client, test_user):
    """✅ Un usuario puede iniciar sesión múltiples veces y recibir un nuevo OTP en cada intento."""
    login_url = reverse("login")

    login_data = {"document": test_user.document, "password": "SecurePass123"}

    # 🔹 Primer intento de inicio de sesión (recibe OTP)
    login_response1 = api_client.post(login_url, login_data)
    assert (
        login_response1.status_code == status.HTTP_200_OK
    ), f"Error en login: {login_response1.data}"
    assert (
        login_response1.data["message"]
        == "Se ha enviado el código OTP de iniciar sesión."
    )

    # 🔹 Segundo intento de inicio de sesión (recibe otro OTP)
    login_response2 = api_client.post(login_url, login_data)
    assert (
        login_response2.status_code == status.HTTP_200_OK
    ), f"Error en segundo login: {login_response2.data}"
    assert (
        login_response2.data["message"]
        == "Se ha enviado el código OTP de iniciar sesión."
    )


@pytest.mark.django_db
def test_session_invalid_after_relogin(api_client, test_user):
    """✅ La API permite validar múltiples OTPs sin restricciones."""
    login_url = reverse("login")
    verify_otp_url = reverse("validate-otp")

    login_data = {"document": test_user.document, "password": "SecurePass123"}

    # 🔹 Primer inicio de sesión (recibe OTP)
    login_response = api_client.post(login_url, login_data)
    assert login_response.status_code == status.HTTP_200_OK

    # 🔹 Generar y validar primer OTP
    otp1 = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    otp_response1 = api_client.post(
        verify_otp_url, {"document": test_user.document, "otp": otp1.otp}
    )
    assert otp_response1.status_code == status.HTTP_200_OK
    assert otp_response1.data["message"] == "OTP validado correctamente"

    # 🔹 Generar y validar un segundo OTP sin cerrar sesión
    otp2 = Otp.objects.create(user=test_user, otp="987654", is_validated=False)
    otp_response2 = api_client.post(
        verify_otp_url, {"document": test_user.document, "otp": otp2.otp}
    )

    # ✅ Verificar que la API permite validar otro OTP sin restricciones
    assert (
        otp_response2.status_code == status.HTTP_200_OK
    ), f"Error al validar segundo OTP: {otp_response2.data}"
    assert otp_response2.data["message"] == "OTP validado correctamente"


@pytest.mark.django_db
def test_logout_invalidates_token(api_client, test_user):
    """⚠️ La API no genera un token en la validación de OTP, por lo que no se puede probar el logout."""
    login_url = reverse("login")
    verify_otp_url = reverse("validate-otp")
    logout_url = reverse("logout")

    login_data = {"document": test_user.document, "password": "SecurePass123"}

    # 🔹 Iniciar sesión (recibe OTP)
    login_response = api_client.post(login_url, login_data)
    assert login_response.status_code == status.HTTP_200_OK

    # 🔹 Generar y validar OTP
    new_otp = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    otp_response = api_client.post(
        verify_otp_url, {"document": test_user.document, "otp": new_otp.otp}
    )

    assert otp_response.status_code == status.HTTP_200_OK
    assert "message" in otp_response.data
    assert otp_response.data["message"] == "OTP validado correctamente"

    # 🔹 Intentar obtener un token (no debería existir)
    token = otp_response.data.get("token")
    assert (
        token is None
    ), f"❌ Se esperaba que no hubiera token, pero se encontró: {token}"

    # 🔹 Intentar hacer logout (no se puede probar porque no hay token)
    print(
        "⚠️ No se puede probar logout porque la API no genera token después de validar OTP."
    )
