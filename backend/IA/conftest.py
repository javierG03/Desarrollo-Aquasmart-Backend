import pytest
from django.utils import timezone
from IA.models import ConsuptionPredictionLot
from django.conf import settings
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
def person_type(db):
    personaNatural = PersonType.objects.create(typeName="Natural")
    personaJuridica = PersonType.objects.create(typeName="Juridica")
    return personaNatural, personaJuridica

@pytest.fixture
def soil_type(db):
    Arcilloso = SoilType.objects.create(
        name="Arcilloso"
        ),
    Arenoso = SoilType.objects.create(
        name="Arenoso"
        )
    return Arcilloso, Arenoso

@pytest.fixture
def crop_type(db):
    Maiz = CropType.objects.create(
        name="Maíz"
        ),
    Tomate = CropType.objects.create(
        name="Tomate"
        )
    return Maiz, Tomate

@pytest.fixture
def users_Plots(users, admin_User):
    activeUser, _, _ = users
    adminUser = admin_User
    
    activeUserActivePlot = Plot.objects.create(
    plot_name="Predio activo de Prueba",
    owner=activeUser,
    is_activate=True,
    latitud=1.1,
    longitud=2.2,
    plot_extension=5.0
    )

    activeUserInactivePlot = Plot.objects.create(
        plot_name="Predio inactivo de Prueba",
        owner=activeUser,
        is_activate=False,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )

    adminUserPlot = Plot.objects.create(
        plot_name = "Predio admin de Prueba",
        owner=adminUser,
        is_activate=True,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )

    adminUserInactivePlot = Plot.objects.create(
        plot_name="Predio admin inactivo de Prueba",
        owner=activeUser,
        is_activate=False,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )
    return activeUserActivePlot, activeUserInactivePlot, adminUserPlot, adminUserInactivePlot

@pytest.fixture
def users_Lots(soil_type, crop_type, users_Plots):
    activeUserActivePlot, adminUserPlot,_,_ = users_Plots
    Maiz, Tomate= crop_type
    Arcilloso, Arenoso = soil_type
    ActiveUserActiveLot1 = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Maiz,
        soil_type=Arcilloso,
        crop_name="Maíz Híbrido",
        crop_variety="Híbrido 123",
        is_activate=True
    ),

    ActiveUserActiveLot2 = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Tomate,
        soil_type=Arenoso,
        crop_name="Tomate Híbrido",
        crop_variety="Híbrido 123",
        is_activate=True
    )
    #Debe de aparecer inactivo al tener un caudal de 0
    ActiveUserInactiveLot = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Maiz,
        soil_type=Arcilloso,
        crop_name="Maíz Feo",
        crop_variety="Feo 123"
    )

    return ActiveUserActiveLot1, ActiveUserActiveLot2, ActiveUserInactiveLot


@pytest.fixture
def device_type():
    valvulaPredios= DeviceType.objects.filter(device_id=VALVE_4_ID), #Importante, sin esto ningún lote será válido
    sensorCaudal = DeviceType.objects.create(name="Sensor de caudal")
    return valvulaPredios, sensorCaudal

@pytest.fixture
def iot_device(users_Plots,users_Lots,device_type):
    activeUserActiveLot1,activeUserActiveLot2,activeUserInactiveLot = users_Lots
    activeUserActivePlot,_,_,_= users_Plots
    valvulaPredios,_ = device_type

    valvulaActiveUserLot1 = IoTDevice.objects.create(
        device_type=valvulaPredios,
        name="Válvula de 4\"",
        iot_id=1,
        id_plot=activeUserActivePlot,
        id_lot=activeUserActiveLot1,
        is_active=True,
        actual_flow=4.0
    ),
    valvulaActiveUserLot2 = IoTDevice.objects.create(
        device_type=valvulaPredios,
        name="Válvula de 4\"",
        iot_id=1,
        id_plot=activeUserActivePlot,
        id_lot=activeUserActiveLot2,
        is_active=True,
        actual_flow=6.0
    )
    valvulaActiveUserInactiveLot =IoTDevice.objects.create(
        device_type=valvulaPredios,
        name="Válvula de 4\"",
        iot_id=1,
        id_plot=activeUserActivePlot,
        id_lot=activeUserInactiveLot,
        actual_flow=0
    )
    return valvulaActiveUserLot1, valvulaActiveUserLot2, valvulaActiveUserInactiveLot

@pytest.fixture
def users (db, person_type):

    
    """Crea un usuario para pruebas."""
    activeUser= CustomUser.objects.create_user(
        document="1234567890",
        first_name="Test",
        last_name="User",
        email="activeUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=person_type,
        is_active=True,
        is_registered=True,
    ),

    #Este usuario se utilizará para los test de un usuario inactivo no debería de...
    inactiveUser = CustomUser.objects.create_user(
        document="01234567890",
        first_name="Test",
        last_name="User",
        email="inactiveUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=person_type,
        is_active=False,
        is_registered=True,
     )
    
    #Este usuario se utilizará para los test de un usuario no deberia poder ver propiedades de otro usuario
    intrudeActiveUser = CustomUser.objects.create_user(
        document="001234567890",
        first_name="Test",
        last_name="User",
        email="intrudeActiveUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=person_type,
        is_active=False,
        is_registered=True,
    )
    return activeUser,inactiveUser,intrudeActiveUser

@pytest.fixture
def staff_user(db,person_type):
    #definición de roles/grupos
    tecnico_group, _ = Group.objects.get_or_create(name="Tecnicos")
    operator_group,_=Group.objects.get_or_create(name="Operadores")

    #creación de staffs
    tecnicoUser= CustomUser.objects.create_superuser(
    document="000111222333444",
    first_name="tecnico",
    last_name="User",
    email="tecnico@example.com",
    phone="11222333444",
    password="UserPass123@",
    person_type=person_type,
    is_registered=True
    )
    operatorUser= CustomUser.objects.create_superuser(
        document="111222333444000",
        first_name="operator",
        last_name="User",
        email="operator@example.com",
        phone="111222333444",
        password="UserPass123@",
        person_type=person_type,
        is_registered=True
    )
    operatorUser.groups.add(operator_group)
    tecnicoUser.groups.add(tecnico_group)
    return tecnicoUser,operatorUser

@pytest.fixture
def admin_user(db,person_type):
    admin_group, _ = Group.objects.get_or_create(name="administrador")
    adminUser = CustomUser.objects.create_superuser(
        document="1122334455",
        first_name="Admin",
        last_name="User",
        email = os.environ.get('EMAIL_HOST_USER', default=os.getenv("EMAIL_HOST_USER")),
        phone="3210000000",
        password="AdminPass123@",  # <- muy importante
        person_type=person_type,
        is_registered=True
    )
    adminUser.groups.add(admin_group)
    return adminUser


@pytest.fixture
def login_and_validate_otp():
    def _login_and_validate(client, user, password):
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