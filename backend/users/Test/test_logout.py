import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import CustomUser, Otp
from rest_framework import status  # ✅ CORRECTO


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


@pytest.mark.django_db
def test_logout(api_client, test_user):
    """✅ Cerrar sesión debe invalidar la sesión del usuario si hay un token activo."""

    login_url = reverse("login")
    verify_otp_url = reverse("validate-otp")
    logout_url = reverse("logout")

    login_data = {"document": test_user.document, "password": "SecurePass123"}

    # 🔹 Iniciar sesión (recibe OTP)
    login_response = api_client.post(login_url, login_data)
    assert (
        login_response.status_code == status.HTTP_200_OK
    ), f"Error en login: {login_response.data}"

    # 🔹 Generar y validar OTP
    otp = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    otp_response = api_client.post(
        verify_otp_url, {"document": test_user.document, "otp": otp.otp}
    )
    assert (
        otp_response.status_code == status.HTTP_200_OK
    ), f"Error en validación OTP: {otp_response.data}"
    assert otp_response.data["message"] == "OTP validado correctamente"

    # 🔹 Intentar obtener un token (no debería existir)
    token = otp_response.data.get("token")
    if token:
        # 🔹 Intentar hacer logout con el token
        headers = {"Authorization": f"Bearer {token}"}
        logout_response = api_client.post(logout_url, **headers)
        assert (
            logout_response.status_code == status.HTTP_200_OK
        ), f"Error en logout: {logout_response.data}"

        # 🔹 Intentar acceder a un endpoint protegido con el token (debe fallar)
        protected_url = reverse(
            "protected-endpoint"
        )  # 🔥 Reemplaza con un endpoint real
        protected_response = api_client.get(protected_url, **headers)
        assert (
            protected_response.status_code == status.HTTP_401_UNAUTHORIZED
        ), "❌ Token sigue activo tras logout"

    else:
        # 🔹 Si no hay token, verificar que logout falle con error
        logout_response = api_client.post(logout_url)
        assert (
            logout_response.status_code == status.HTTP_401_UNAUTHORIZED
        ), f"❌ Logout debería fallar sin token: {logout_response.data}"
        print(
            "⚠️ No se puede probar logout porque la API no genera un token tras validar OTP."
        )
