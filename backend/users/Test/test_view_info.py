import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import CustomUser, PersonType, Otp
from rest_framework import status  # ✅ Correcto
from rest_framework.test import force_authenticate


@pytest.fixture
def api_client():
    """Cliente API para realizar las solicitudes de prueba."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Usuario de prueba ya registrado en la base de datos."""

    person_type = PersonType.objects.create(typeName="Natural")  # ✅ Corrección: Crear instancia de PersonType

    return CustomUser.objects.create_user(
        document="123456789012",
        first_name="John",
        last_name="Doe",
        email="johndoe@example.com",
        phone="1234567890",
        password="SecurePass123",
        address="Calle 123",
        person_type=person_type,  # ✅ Se asigna la instancia, no un string
        is_active=True,
        is_registered=True,
    )
from rest_framework.test import force_authenticate

@pytest.mark.django_db
def test_view_personal_data_authenticated(api_client, test_user):
    """✅ Un usuario autenticado debe poder ver su información personal."""

    profile_url = reverse("perfil-usuario")
    login_url = reverse("login")
    verify_otp_url = reverse("validate-otp")

    # 🔹 Iniciar sesión
    login_data = {"document": test_user.document, "password": "SecurePass123"}
    login_response = api_client.post(login_url, login_data)
    assert login_response.status_code == status.HTTP_200_OK, f"Error en login: {login_response.data}"

    # 🔹 Generar y validar OTP
    otp = Otp.objects.create(user=test_user, otp="654321", is_validated=False)
    otp_response = api_client.post(verify_otp_url, {"document": test_user.document, "otp": otp.otp})

    print("🔹 API OTP RESPONSE:", otp_response.data)  # Depuración

    assert otp_response.status_code == status.HTTP_200_OK, f"Error en validación OTP: {otp_response.data}"

    # 🔹 Obtener el token de la respuesta (verificar la clave exacta)
    token = otp_response.data.get("token")
    assert token, f"❌ No se recibió un token tras validar el OTP. Respuesta: {otp_response.data}"

    # 🔹 Autenticarse con el token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # 🔹 Intentar acceder a la información personal
    profile_response = api_client.get(profile_url)

    print("🔹 API PROFILE RESPONSE:", profile_response.data)  # Depuración

    # ✅ Verificar acceso a la información personal
    assert profile_response.status_code == status.HTTP_200_OK, f"Error al obtener datos personales: {profile_response.data}"
    assert "document" in profile_response.data, "❌ No se encontraron los datos personales en la respuesta."









@pytest.mark.django_db
def test_view_personal_data_unauthenticated(api_client):
    """❌ Un usuario no autenticado NO debe poder ver datos personales."""

    # 🔹 Verificar la URL correcta en `urls.py`
    try:
        profile_url = reverse("perfil-usuario")  # ✅ Verificar que el nombre sea correcto en `urls.py`
    except:
        pytest.fail("❌ No se encontró la URL 'perfil-usuario'. Verifica las rutas en `urls.py`.")

    # 🔹 Intentar obtener los datos personales sin autenticación
    response = api_client.get(profile_url)

    # ✅ Debe fallar con 401 (No autorizado)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, f"❌ Acceso no autorizado permitido: {response.data}"
    assert "detail" in response.data
    assert response.data["detail"] == "Las credenciales de autenticación no se proveyeron."
