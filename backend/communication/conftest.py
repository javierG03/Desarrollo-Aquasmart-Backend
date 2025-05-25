import pytest
from django.urls import reverse
from users.models import Otp, CustomUser, PersonType
from iot.models import DeviceType, IoTDevice, VALVE_4_ID
from rest_framework.test import APIClient
from rest_framework import status
from plots_lots.models import Plot, Lot, SoilType, CropType
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import os


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def soil_type(db):
    """Crea un tipo de suelo para las pruebas."""
    return SoilType.objects.create(name="Arcilloso")

@pytest.fixture
def crop_type(db):
    return CropType.objects.create(name="Maíz")

@pytest.fixture
def device_type():
    sensorHumedad = DeviceType.objects.create(name="Sensor de humedad")
    sensorCaudal = DeviceType.objects.create(name="Sensor de caudal")
    valvulaBocatoma = DeviceType.objects.create(name="Válvula de bocatoma")
    TuberiaPredios = DeviceType.objects.create(name="Tubería de 4\"")
    TuberiaBocatoma = DeviceType.objects.create(name="Tubería de 48\"")
    sensorTemperatura = DeviceType.objects.create(name="Sensor de temperatura")
    valvulaPredios = DeviceType.objects.filter(device_id=VALVE_4_ID).first()
    return sensorHumedad, sensorCaudal, sensorTemperatura, valvulaBocatoma, TuberiaBocatoma, TuberiaPredios, valvulaPredios

@pytest.fixture
def person_type(db):
    return PersonType.objects.create(typeName= "Natural")

@pytest.fixture
def admin_user(db, person_type):
    user = CustomUser.objects.create_superuser(
        document="01234567890",
        first_name="Admin",
        last_name="User",
        email = os.environ.get('EMAIL_HOST_USER', default=os.getenv("EMAIL_HOST_USER")),
        phone="3210000000",
        password="AdminPass123@",  # <- muy importante
        person_type=person_type,
        is_registered=True

            
    )
    group, _ = Group.objects.get_or_create(name="Administradores")
    user.groups.add(group)
    user.save()
    return user

@pytest.fixture
def tecnico_user(db,person_type):
    user = CustomUser.objects.create_superuser(
    document="00123456789",
    first_name="tecnico",
    last_name="User",
    email="tecnico@example.com",
    phone="000111222333444",
    password="UserPass123@",
    person_type=person_type,
    is_registered=True
    )
    group, _ = Group.objects.get_or_create(name="Tecnicos")
    user.groups.add(group)
    user.save()
    return user

@pytest.fixture
def operador_user(db, person_type):
    user = CustomUser.objects.create_superuser(
    first_name="operador",
    last_name="User",
    email="operador@example.com",
    password="UserPass123@",
    document="0001234567890",
    phone="11122233344455566",
    person_type=person_type,
    is_registered=True
    )
    group, _ = Group.objects.get_or_create(name="Operador")
    user.groups.add(group)
    user.save()
    return user

@pytest.fixture
def normal_user(db, person_type):
    """Crea un usuario normal (no administrador)"""
    user = CustomUser.objects.create_user(
        document="123456789012",
        first_name="Regular",
        last_name="User",
        email="user@example.com",
        phone="3000000000",
        password="UserPass123@",
        person_type=person_type,
        is_registered=True
    )
    group, _ = Group.objects.get_or_create(name="Usuario")
    user.groups.add(group)
    user.save()
    return user



@pytest.fixture
def user_plot(normal_user):
    
    return Plot.objects.create(
        plot_name="Predio Prueba",
        owner=normal_user,
        is_activate=True,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )


@pytest.fixture
def inactive_user_plot(normal_user):
    
    return Plot.objects.create(
        plot_name="Predio Inactivo",
        owner=normal_user,
        is_activate=False,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )


@pytest.fixture
def user_lot(user_plot, crop_type, soil_type):
    lote1 = Lot.objects.create(
        plot=user_plot,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Maíz Híbrido",
        crop_variety="Híbrido 123",
        is_activate=True
    )
    lote2 = Lot.objects.create(
        plot=user_plot,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Maíz cafe",
        crop_variety="cafe 123",
        is_activate=True
    )

    lote3 = Lot.objects.create(
        plot=user_plot,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Maíz cafe",
        crop_variety="cafe 123",
        is_activate=False
    )
    
    return lote1, lote2, lote3


@pytest.fixture
def iot_device(user_plot,user_lot, device_type):
    sensorHumedad, sensorCaudal, sensorTemperatura, valvulaBocatoma, TuberiaBocatoma, TuberiaPredios, valvulaPredios = device_type
    lote1, lote2, lote3 = user_lot
    
    valvula4 = IoTDevice.objects.create(
        device_type=valvulaPredios,
        name="Válvula de 4\"",
        iot_id=1,
        id_plot=user_plot,
        id_lot=lote1,
        is_active=True,
        actual_flow=4.0

    )
    tuberia4 = IoTDevice.objects.create(
        device_type=TuberiaPredios,
        name="Tubería de 4\"",
        iot_id=2,
        id_plot=user_plot,
        id_lot=lote1,
        is_active=True
    )
    sensorDeCaudal = IoTDevice.objects.create(
        device_type=sensorCaudal,
        name="Sensor de caudal",
        iot_id=3,
        id_plot=user_plot,
        id_lot=lote1,
        is_active=True
    )

    valvula4Lote3 = IoTDevice.objects.create(
        device_type=valvulaPredios,
        name="Valvula 4\"",
        iot_id=4,
        id_plot=user_plot,
        id_lot=lote3,
        is_active=True,
        actual_flow=4.0
    )
    return valvula4, tuberia4, sensorDeCaudal, valvula4Lote3



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





