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
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import os

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def person_type(db):
    personaNatural = PersonType.objects.create(typeName="Natural")
    personaJuridica = PersonType.objects.create(typeName="Juridica")
    return personaNatural, personaJuridica

@pytest.fixture
def soil_type(db):
    Arcilloso = SoilType.objects.create(name="Arcilloso")
    Arenoso = SoilType.objects.create(name="Arenoso")
    return Arcilloso, Arenoso

@pytest.fixture
def crop_type(db):
    Maiz = CropType.objects.create(name="Maíz")
    Tomate = CropType.objects.create(name="Tomate")
    return Maiz, Tomate

@pytest.fixture
def prediction_permissions(db):
    """Obtiene los permisos existentes para predicciones."""
    # Los permisos ya fueron creados por las migraciones de AquaSmart
    # Solo necesitamos obtenerlos
    
    try:
        content_type = ContentType.objects.get(
            model="aquasmart_permission", 
            app_label="AquaSmart"
        )
    except ContentType.DoesNotExist:
        pytest.skip("ContentType para AquaSmart no existe. Ejecutar migraciones primero.")
    
    permissions = {}
    
    # Lista de permisos que deberían existir (desde las migraciones)
    prediction_perms = [
        "ver_predicciones_lotes",
        "generar_predicciones_lotes", 
        "eliminar_predicciones_lotes",
        "ver_prediccion_consumo_mi_lote",
        "generar_prediccion_consumo_mi_lote",
        "eliminar_prediccion_consumo_mi_lote",
        "generar_prediccion_distrito",
        "ver_predicciones_distrito",
        "eliminar_prediccion_distrito",
    ]
    
    # Obtener permisos existentes
    for codename in prediction_perms:
        try:
            perm = Permission.objects.get(
                codename=codename,
                content_type=content_type
            )
            permissions[codename] = perm
        except Permission.DoesNotExist:
            print(f"Warning: Permiso '{codename}' no encontrado. Puede que falten migraciones.")
    
    return permissions

@pytest.fixture
def device_type(db):
    """Crea los tipos de dispositivos necesarios."""
    # Asegurar que el tipo de válvula 4" existe
    valvula_4_type, created = DeviceType.objects.get_or_create(
        device_id=VALVE_4_ID,
        defaults={'name': 'Válvula 4"'}
    )
    sensor_caudal_type = DeviceType.objects.create(name="Sensor de caudal")
    return valvula_4_type, sensor_caudal_type

@pytest.fixture
def users(db, person_type, prediction_permissions):
    """Crea usuarios para pruebas con permisos correctos."""
    personaNatural, _ = person_type
    
    activeUser = CustomUser.objects.create_user(
        document="1234567890",
        first_name="Test",
        last_name="User",
        email="activeUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=personaNatural,
        is_active=True,
        is_registered=True
    )

    inactiveUser = CustomUser.objects.create_user(
        document="01234567890",
        first_name="Test",
        last_name="User",
        email="inactiveUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=personaNatural,
        is_active=False,
        is_registered=True
    )
    
    intrudeActiveUser = CustomUser.objects.create_user(
        document="001234567890",
        first_name="Test",
        last_name="User",
        email="intrudeActiveUser@example.com",
        phone="1234567890",
        password="UserPass123@",
        person_type=personaNatural,
        is_active=True,  # Corregido: debe estar activo para funcionar
        is_registered=True
    )
    
    # Asignar permisos al usuario normal para sus propios lotes
    user_perms = [
        "ver_prediccion_consumo_mi_lote",
        "generar_prediccion_consumo_mi_lote",
        "eliminar_prediccion_consumo_mi_lote"
    ]
    
    for user in [activeUser, inactiveUser, intrudeActiveUser]:
        for perm_name in user_perms:
            if perm_name in prediction_permissions:
                user.user_permissions.add(prediction_permissions[perm_name])

    return activeUser, inactiveUser, intrudeActiveUser

@pytest.fixture
def users_Plots(users, admin_user):
    activeUser, _, _ = users
    adminUser = admin_user
    
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
        plot_name="Predio admin de Prueba",
        owner=adminUser,
        is_activate=True,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )

    adminUserInactivePlot = Plot.objects.create(
        plot_name="Predio admin inactivo de Prueba",
        owner=adminUser,  # Corregido: debe ser adminUser, no activeUser
        is_activate=False,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )
    return activeUserActivePlot, activeUserInactivePlot, adminUserPlot, adminUserInactivePlot

@pytest.fixture
def users_Lots(soil_type, crop_type, users_Plots):
    activeUserActivePlot, _, adminUserPlot, _ = users_Plots
    Maiz, Tomate = crop_type
    Arcilloso, Arenoso = soil_type
    
    ActiveUserActiveLot1 = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Maiz,
        soil_type=Arcilloso,
        crop_name="Maíz Híbrido",
        crop_variety="Híbrido 123",
        is_activate=True
    )

    ActiveUserActiveLot2 = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Tomate,
        soil_type=Arenoso,
        crop_name="Tomate Híbrido",
        crop_variety="Híbrido 123",
        is_activate=True
    )
    
    # Debe aparecer inactivo al tener un caudal de 0
    ActiveUserInactiveLot = Lot.objects.create(
        plot=activeUserActivePlot,
        crop_type=Maiz,
        soil_type=Arcilloso,
        crop_name="Maíz Feo",
        crop_variety="Feo 123",
        is_activate=False  # Explícitamente inactivo
    )

    return ActiveUserActiveLot1, ActiveUserActiveLot2, ActiveUserInactiveLot

@pytest.fixture
def iot_device(users_Plots, users_Lots, device_type):
    activeUserActiveLot1, activeUserActiveLot2, activeUserInactiveLot = users_Lots
    activeUserActivePlot, _, _, _ = users_Plots
    valvula_4_type, _ = device_type

    valvulaActiveUserLot1 = IoTDevice.objects.create(
        device_type=valvula_4_type,  # Usar el objeto directamente
        name="Válvula de 4\" Lote 1",
        id_plot=activeUserActivePlot,
        id_lot=activeUserActiveLot1,
        is_active=True,
        actual_flow=4.0
    )
    
    valvulaActiveUserLot2 = IoTDevice.objects.create(
        device_type=valvula_4_type,
        name="Válvula de 4\" Lote 2",
        id_plot=activeUserActivePlot,
        id_lot=activeUserActiveLot2,
        is_active=True,
        actual_flow=6.0
    )
    
    valvulaActiveUserInactiveLot = IoTDevice.objects.create(
        device_type=valvula_4_type,
        name="Válvula de 4\" Lote Inactivo",
        id_plot=activeUserActivePlot,
        id_lot=activeUserInactiveLot,
        is_active=False,  # Dispositivo inactivo
        actual_flow=0
    )
    
    return valvulaActiveUserLot1, valvulaActiveUserLot2, valvulaActiveUserInactiveLot

@pytest.fixture
def staff_user(db, person_type, prediction_permissions):
    personaNatural, _ = person_type

    # Definición de roles/grupos
    tecnico_group, _ = Group.objects.get_or_create(name="Tecnicos")
    operator_group, _ = Group.objects.get_or_create(name="Operadores")

    # Creación de staffs
    tecnicoUser = CustomUser.objects.create_superuser(
        document="000111222333444",
        first_name="tecnico",
        last_name="User",
        email="tecnico@example.com",
        phone="11222333444",
        password="UserPass123@",
        person_type=personaNatural,
        is_registered=True
    )
    
    operatorUser = CustomUser.objects.create_superuser(
        document="111222333444000",
        first_name="operator",
        last_name="User",
        email="operator@example.com",
        phone="111222333444",
        password="UserPass123@",
        person_type=personaNatural,
        is_registered=True
    )
    
    # Asignar grupos
    operatorUser.groups.add(operator_group)
    tecnicoUser.groups.add(tecnico_group)
    
    # Asignar permisos completos de predicción a staff
    staff_perms = [
        "ver_predicciones_lotes",
        "generar_predicciones_lotes",
        "eliminar_predicciones_lotes",
        "generar_prediccion_distrito",
        "ver_predicciones_distrito",
        "eliminar_prediccion_distrito"
    ]
    
    for user in [tecnicoUser, operatorUser]:
        for perm_name in staff_perms:
            if perm_name in prediction_permissions:
                user.user_permissions.add(prediction_permissions[perm_name])
    
    return tecnicoUser, operatorUser

@pytest.fixture
def admin_user(db, person_type, prediction_permissions):
    personaNatural, _ = person_type
    admin_group, _ = Group.objects.get_or_create(name="Administradores")
    
    adminUser = CustomUser.objects.create_superuser(
        document="1122334455",
        first_name="Admin",
        last_name="User",
        email=os.environ.get('EMAIL_HOST_USER', default=os.getenv("EMAIL_HOST_USER")),
        phone="3210000000",
        password="AdminPass123@",
        person_type=personaNatural,
        is_registered=True
    )
    
    adminUser.groups.add(admin_group)
    
    # Asignar todos los permisos de predicción al admin
    for perm in prediction_permissions.values():
        adminUser.user_permissions.add(perm)
    
    return adminUser

@pytest.fixture
def login_and_validate_otp():
    def _login_and_validate(client, user, password=None):
        if password is None:
            # Determinar contraseña por tipo de usuario
            if user.is_superuser:
                password = "AdminPass123@"
            else:
                password = "UserPass123@"
        
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