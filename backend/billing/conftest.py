import pytest
from django.urls import reverse
from users.models import Otp, CustomUser, PersonType

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def person_type(db):
    return PersonType.objects.create(typeName="Natural")

@pytest.fixture
def admin_user(db, person_type):
    user = CustomUser.objects.create_superuser(
        document="admin123",
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone="3210000000",
        password="AdminPass123@",  # <- muy importante
        person_type=person_type,
        is_registered=True
    )
    return user



@pytest.fixture
def login_and_validate_otp():
    def _login_and_validate(client, user, password="AdminPass123@"):
        login_url = reverse("login")
        login_data = {"document": user.document, "password": password}
        login_response = client.post(login_url, login_data)
        assert login_response.status_code == 200

        otp = Otp.objects.filter(user=user, is_login=True).first()
        assert otp is not None

        validate_url = reverse("validate-otp")
        otp_response = client.post(validate_url, {"document": user.document, "otp": otp.otp})
        assert otp_response.status_code == 200

        token = otp_response.data["token"]
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return client
    return _login_and_validate
