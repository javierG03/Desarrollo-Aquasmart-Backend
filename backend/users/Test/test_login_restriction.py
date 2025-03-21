import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser, LoginRestriction
from django.utils.timezone import now, timedelta


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    """Usuario activo y registrado"""
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
def restricted_user(db):
    """Usuario bloqueado por múltiples intentos fallidos"""
    user = CustomUser.objects.create_user(
        document="000000000000",
        first_name="Restricted",
        last_name="User",
        email="restricted@example.com",
        phone="1111111111",
        password="BlockedPass123",
        is_active=True,
        is_registered=True,
    )
    LoginRestriction.objects.create(
        user=user, attempts=5, blocked_until=now() + timedelta(minutes=30)
    )
    return user


@pytest.fixture
def temporarily_blocked_user(db):
    """Usuario con intentos fallidos pero aún sin bloqueo total"""
    user = CustomUser.objects.create_user(
        document="111111111111",
        first_name="TempBlocked",
        last_name="User",
        email="tempblocked@example.com",
        phone="2222222222",
        password="TempBlocked123",
        is_active=True,
        is_registered=True,
    )
    LoginRestriction.objects.create(
        user=user, attempts=4, blocked_until=None
    )  # Aún no bloqueado
    return user


@pytest.mark.django_db
def test_login_attempts_exceeded(api_client, test_user):
    """❌ Intentar más de 5 veces con contraseña incorrecta bloquea al usuario."""
    url = reverse("login")

    for _ in range(5):  # 5 intentos fallidos
        response = api_client.post(
            url, {"document": test_user.document, "password": "WrongPass"}
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Usuario bloqueado por 30 minutos." in response.data["error"]["detail"][0]


@pytest.mark.django_db
def test_login_while_temporarily_blocked(api_client, temporarily_blocked_user):
    """⚠️ Usuario con 4 intentos fallidos aún puede intentar login."""
    url = reverse("login")
    response = api_client.post(
        url, {"document": temporarily_blocked_user.document, "password": "WrongPass"}
    )

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    )  # No está bloqueado aún, pero sigue fallando
    assert "Credenciales inválidas." in response.data["error"]["detail"]


@pytest.mark.django_db
def test_login_while_temporarily_blocked(api_client, temporarily_blocked_user):
    """⚠️ Usuario con 4 intentos fallidos aún puede intentar login, pero el intento 5 lo bloquea."""
    url = reverse("login")

    # Intento fallido número 5
    response = api_client.post(
        url, {"document": temporarily_blocked_user.document, "password": "WrongPass"}
    )

    # Recuperamos el objeto actualizado
    login_restriction = LoginRestriction.objects.get(user=temporarily_blocked_user)
    login_restriction.refresh_from_db()

    # 🔴 En este punto, el usuario debe estar bloqueado
    assert (
        login_restriction.is_blocked()
    ), "El usuario debería estar bloqueado tras el 5° intento."

    # Verificamos que `attempts` se haya reiniciado a 0 tras el bloqueo
    assert (
        login_restriction.attempts == 0
    ), f"Se esperaba 0 intentos tras el bloqueo, pero se encontraron {login_restriction.attempts}"

    # Verificar si el mensaje de bloqueo es el esperado
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Usuario bloqueado por 30 minutos." in response.data["error"]["detail"][0]
    ), f"Mensaje inesperado: {response.data['error']['detail'][0]}"


@pytest.mark.django_db
def test_login_while_blocked(api_client, restricted_user):
    """❌ Usuario bloqueado aún no puede iniciar sesión."""
    url = reverse("login")
    response = api_client.post(
        url, {"document": restricted_user.document, "password": "BlockedPass123"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Demasiados intentos fallidos." in response.data["error"]["detail"][0]
