import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser, LoginRestriction, Otp
from django.utils.timezone import now, timedelta  # Asegurar importación correcta


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
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
def blocked_user(db):
    user = CustomUser.objects.create_user(
        document="000000000000",
        first_name="Blocked",
        last_name="User",
        email="blocked@example.com",
        phone="9876543210",
        password="BlockedPass123",
        is_active=True,
        is_registered=True,
    )
    LoginRestriction.objects.create(
        user=user, attempts=5, blocked_until="2099-01-01 00:00:00"
    )
    return user


@pytest.fixture
def inactive_user(db):
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


@pytest.mark.django_db
def test_login_success(api_client, test_user):
    url = reverse("login")
    data = {"document": "123456789012", "password": "SecurePass123"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data


@pytest.mark.django_db
def test_login_user_not_found(api_client):
    url = reverse("login")
    data = {"document": "999999999999", "password": "FakePass"}
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verificar si error es string o lista
    error_message = response.data.get("error", "")
    if isinstance(error_message, list):
        error_message = " ".join([str(err) for err in error_message])

    assert "No se encontró un usuario con este documento." in error_message




@pytest.mark.django_db
def test_login_wrong_password(api_client, test_user):
    url = reverse("login")
    data = {"document": "123456789012", "password": "WrongPass"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_message = str(response.data["error"]["detail"])
    assert "credenciales inválidas" in error_message.lower() or "usuario bloqueado" in error_message.lower()






@pytest.mark.django_db
def test_login_blocked_user(api_client, blocked_user):
    url = reverse("login")
    data = {"document": "000000000000", "password": "BlockedPass123"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Demasiados intentos fallidos." in response.data["error"]["detail"][0]


@pytest.mark.django_db
def test_login_inactive_user(api_client, inactive_user):
    url = reverse("login")
    data = {"document": "111111111111", "password": "InactivePass123"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.data["error"]["detail"]
        == "Su cuenta está inactiva. Póngase en contacto con el servicio de soporte."
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad_input", ["' OR '1'='1", "admin' --", "password' DROP TABLE users;"]
)
def test_login_sql_injection_password(api_client, bad_input):
    url = reverse("login")
    data = {"document": "123456789012", "password": bad_input}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_login_empty_password(api_client, test_user):
    url = reverse("login")
    data = {"document": "123456789012", "password": ""}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_brute_force_protection(api_client, test_user):
    url = reverse("login")
    for _ in range(5):
        response = api_client.post(
            url, {"document": "123456789012", "password": "WrongPass"}
        )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Usuario bloqueado por 30 minutos." in response.data["error"]["detail"][0]


@pytest.fixture
def unregistered_user(db):
    """Usuario que no ha completado el pre-registro."""
    return CustomUser.objects.create_user(
        document="222222222222",
        first_name="Unregistered",
        last_name="User",
        email="unregistered@example.com",
        phone="4444444444",
        password="UnregisteredPass123",
        is_active=True,
        is_registered=False,  # No ha completado el pre-registro
    )


@pytest.fixture
def deleted_user(db):
    """Usuario eliminado (soft delete o is_active=False)."""
    user = CustomUser.objects.create_user(
        document="333333333333",
        first_name="Deleted",
        last_name="User",
        email="deleted@example.com",
        phone="6666666666",
        password="DeletedPass123",
        is_active=False,  # Simula usuario eliminado
        is_registered=True,
    )
    return user


# -------------------- 🚀 NUEVAS PRUEBAS --------------------
@pytest.mark.django_db
@pytest.mark.parametrize("invalid_document", ["", "123", "12345678901234567890", "@invalid!", "abcd1234"])
def test_login_invalid_document(api_client, invalid_document):
    """❌ Documento con longitud incorrecta o caracteres inválidos."""
    url = reverse("login")
    data = {"document": invalid_document, "password": "SecurePass123"}
    response = api_client.post(url, data)

    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    # Manejar error como string
    error_message = response.data.get("error", "")
    if isinstance(error_message, dict) and "document" in error_message:
        error_message = " ".join([str(err) for err in error_message["document"]])

    error_message = error_message.lower()

    assert (
        "documento inválido" in error_message
        or "no se encontró un usuario" in error_message
        or "este campo no puede estar en blanco" in error_message
        or "asegúrese de que este campo no tenga más de 12 caracteres" in error_message
    )






@pytest.mark.django_db
def test_login_unregistered_user(api_client, unregistered_user):
    """❌ Usuario no registrado intentando iniciar sesión."""
    url = reverse("login")
    data = {"document": "222222222222", "password": "UnregisteredPass123"}
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Convertimos el error en string y verificamos si contiene "pre-registro"
    error_message = str(response.data["error"]["detail"])
    assert "pre-registro" in error_message.lower()


@pytest.mark.django_db
def test_login_deleted_user(api_client, deleted_user):
    """❌ Usuario eliminado intentando iniciar sesión."""
    url = reverse("login")
    data = {"document": "333333333333", "password": "DeletedPass123"}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Su cuenta está inactiva." in response.data["error"]["detail"]


@pytest.mark.django_db
def test_login_expired_block(api_client, blocked_user):
    """✅ Bloqueo de usuario expira tras el tiempo adecuado."""
    login_restriction = LoginRestriction.objects.get(
        user=blocked_user
    )  # Obtener el objeto real

    # Simulamos que el tiempo de bloqueo ha pasado
    login_restriction.blocked_until = now() - timedelta(minutes=1)
    login_restriction.save()

    # Volvemos a recuperar el objeto para asegurarnos de que el cambio se aplicó
    login_restriction.refresh_from_db()
    assert (
        login_restriction.blocked_until < now()
    ), "El bloqueo aún no ha expirado en la BD"

    url = reverse("login")
    data = {"document": "000000000000", "password": "BlockedPass123"}
    response = api_client.post(url, data)

    # Si el bloqueo expiró, debería permitir un nuevo intento (aunque la contraseña sea incorrecta)
    assert response.status_code == status.HTTP_200_OK


@pytest.fixture
def otp_for_user(db, test_user):
    """Genera un OTP válido para el usuario"""
    return Otp.objects.create(user=test_user, otp="123456", is_validated=False)


# -------------------- 🚀 NUEVAS PRUEBAS DE OTP --------------------
@pytest.mark.django_db
@pytest.mark.parametrize("invalid_otp", ["ABC123", "12@34!", "12345"])
def test_invalid_otp(api_client, test_user, otp_for_user, invalid_otp):
    """❌ No permitir letras, caracteres especiales o menos de 6 dígitos en el OTP"""
    url = reverse(
        "validate-otp"
    )  # Asegúrate de que esta es la URL correcta para validar OTP
    data = {"document": test_user.document, "otp": invalid_otp}
    response = api_client.post(url, data)

    

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Acceder correctamente al mensaje de error
    error_message = response.data.get("detail", [""])[
        0
    ]  # Obtener el mensaje si está en lista

    assert (
        "OTP inválido" in error_message
    ), f"Mensaje de error inesperado: {error_message}"


# @pytest.fixture
# def expired_otp(db, test_user):
#     """Genera un OTP que simula estar caducado."""
#     return Otp.objects.create(user=test_user, otp="654321", is_validated=False)


@pytest.fixture
def reused_otp(db, test_user):
    """Genera un OTP ya utilizado para el usuario"""
    return Otp.objects.create(user=test_user, otp="111111", is_validated=True)


# @pytest.mark.django_db
# def test_expired_otp(api_client, test_user, expired_otp, monkeypatch):
#     """❌ OTP caducado no debe ser aceptado."""

#     # Simulamos que la validación del OTP considera el OTP como caducado
#     def mock_is_expired(otp):
#         return True  # Forzar que el OTP se considere caducado

#     monkeypatch.setattr(Otp, "is_expired", mock_is_expired)

#     url = reverse("validate-otp")
#     data = {"document": "123456789012", "otp": "654321"}
#     response = api_client.post(url, data)

#     assert response.status_code == status.HTTP_400_BAD_REQUEST
#     assert "OTP ha caducado" in response.data["detail"][0]


@pytest.mark.django_db
def test_reused_otp(api_client, test_user, reused_otp):
    """❌ OTP ya utilizado no debe ser aceptado."""
    url = reverse("validate-otp")
    data = {"document": "123456789012", "otp": "111111"}
    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "ya ha sido utilizado" in response.data["detail"][0]
    ), f"Mensaje inesperado: {response.data['detail'][0]}"
