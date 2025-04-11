import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from users.models import CustomUser, PersonType
from plots_lots.models import Plot, Lot, CropType, SoilType
from users.models import Otp


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def person_type():
    return PersonType.objects.create(typeName="Natural")


@pytest.fixture
def crop_type():
    return CropType.objects.create(name="Maíz")


@pytest.fixture
def soil_type():
    return SoilType.objects.create(name="Franco")


@pytest.fixture
def admin_user(person_type):
    return CustomUser.objects.create_superuser(
        document="123456789012",
        password="AdminPass123*",
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone="3209999999",
        person_type=person_type,
        is_registered=True,
    )


@pytest.fixture
def normal_user(person_type):
    return CustomUser.objects.create_user(
        document="123456789013",
        password="SecurePass123",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="3000000000",
        person_type=person_type,
        is_registered=True,
    )


@pytest.fixture
def plot(normal_user):
    return Plot.objects.create(
        plot_name="Mi Predio",
        owner=normal_user,
        is_activate=True,
        latitud=1.234,
        longitud=2.345,
        plot_extension=5.0,
    )


@pytest.fixture
def admin_plot(admin_user):
    return Plot.objects.create(
        plot_name="Predio Admin",
        owner=admin_user,
        is_activate=True,
        latitud=3.1415,
        longitud=-75.123,
        plot_extension=7.5,
    )


@pytest.fixture
def registered_lots(plot, crop_type, soil_type):
    return Lot.objects.create(
        plot=plot,
        crop_type=crop_type,
        crop_name="Lote A",
        crop_variety="Variedad A",
        soil_type=soil_type,
        is_activate=True,
    )


@pytest.fixture
def admin_registered_lots(admin_plot, crop_type, soil_type):
    return Lot.objects.create(
        plot=admin_plot,
        crop_type=crop_type,
        crop_name="Lote Admin",
        crop_variety="Variedad X",
        soil_type=soil_type,
        is_activate=True,
    )

@pytest.fixture
def login_and_validate_otp():
    def _login_and_validate(user, client, password="SecurePass123*"):
        login_url = reverse("login")
        login_data = {"document": user.document, "password": password}
        login_response = client.post(login_url, login_data)
        assert login_response.status_code == 200

        from users.models import Otp
        otp = Otp.objects.filter(user=user, is_login=True).first()
        assert otp is not None, f"No se encontró OTP para el usuario {user.document}"

        otp_url = reverse("validate-otp")
        otp_data = {"document": user.document, "otp": otp.otp}
        otp_response = client.post(otp_url, otp_data)
        assert otp_response.status_code == 200

        return otp_response.data["token"]
    return _login_and_validate

