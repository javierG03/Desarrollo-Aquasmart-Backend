import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from django.contrib.auth import get_user_model
from dateutil import parser
from caudal.models import FlowMeasurementPredio
from plots_lots.models import Plot, SoilType
from iot.models import IoTDevice, DeviceType
from django.contrib.auth.models import Group

User = get_user_model()

# 🔹 FIXTURES

@pytest.fixture
def ensure_groups_exist(db):
    """Crear grupos de usuarios si no existen."""
    group_admin, _ = Group.objects.get_or_create(id=1, name="Administrador")
    group_fincario, _ = Group.objects.get_or_create(id=2, name="Fincario")
    print(f"✅ Grupos creados: {group_admin.name}, {group_fincario.name}")

@pytest.fixture
def create_admin_user(db, ensure_groups_exist):
    """Crear usuario administrador."""
    user = User.objects.create_user(
        document="1003916278", 
        first_name="Admin", 
        last_name="User", 
        email="admin@example.com", 
        phone="1234567890", 
        password="Sergio.2025*",
        is_staff=True,
        is_active=True,
        is_registered=True
    )
    group = Group.objects.get(name="Administrador")
    user.groups.add(group)
    print(f"✅ Usuario administrador creado: {user.document}")
    return user

@pytest.fixture
def create_fincario_user(db, ensure_groups_exist):
    """Crear usuario fincario."""
    user = User.objects.create_user(
        document="12110503", 
        first_name="Fincario", 
        last_name="User", 
        email="fincario@example.com", 
        phone="0987654321", 
        password="Sergio.2025*",
        is_staff=False,
        is_active=True,
        is_registered=True
    )
    group = Group.objects.get(name="Fincario")
    user.groups.add(group)
    print(f"✅ Usuario fincario creado: {user.document}")
    return user

@pytest.fixture
def create_predios(db, create_admin_user, create_fincario_user):
    """Crear predios para diferentes usuarios."""
    predio_admin = Plot.objects.create(
        plot_name="Predio Administrador", 
        owner=create_admin_user, 
        latitud=1.0, 
        longitud=1.0, 
        plot_extension=100.0
    )
    predio_fincario = Plot.objects.create(
        plot_name="Predio Fincario", 
        owner=create_fincario_user, 
        latitud=2.0, 
        longitud=2.0, 
        plot_extension=200.0
    )
    print(f"✅ Predios creados: {predio_admin.plot_name}, {predio_fincario.plot_name}")
    return predio_admin, predio_fincario

@pytest.fixture
def create_device_type(db):
    """Crear un tipo de dispositivo."""
    device_type = DeviceType.objects.create(name="Sensor de Flujo")
    print(f"✅ Tipo de dispositivo creado: {device_type.name}")
    return device_type

@pytest.fixture
def create_test_devices(db, create_predios, create_device_type):
    """Crear dispositivos IoT para los predios."""
    predio_admin, predio_fincario = create_predios
    device_type = create_device_type

    device_admin = IoTDevice.objects.create(
        name="Sensor Administrador", 
        id_plot=predio_admin, 
        device_type=device_type
    )
    device_fincario = IoTDevice.objects.create(
        name="Sensor Fincario", 
        id_plot=predio_fincario, 
        device_type=device_type
    )

    print(f"✅ Dispositivos IoT creados: {device_admin.name}, {device_fincario.name}")
    return device_admin, device_fincario


@pytest.fixture
def create_flow_measurements(db, create_test_devices, create_predios):
    
    predio_admin, predio_fincario = create_predios
    device_admin, device_fincario = create_test_devices

    now = timezone.now()
    six_months_ago = now - timezone.timedelta(days=180)

    # Preparar lista de mediciones a crear
    measurement_data = [
        {
            'plot': predio_admin, 
            'device': device_admin, 
            'timestamp': now - timezone.timedelta(days=150), 
            'flow_rate': 15.5
        },
        {
            'plot': predio_fincario, 
            'device': device_fincario, 
            'timestamp': now - timezone.timedelta(days=150), 
            'flow_rate': 14.8
        },
        {
            'plot': predio_admin, 
            'device': device_admin, 
            'timestamp': now - timezone.timedelta(days=210), 
            'flow_rate': 13.2
        }
    ]


    # Crear mediciones filtradas
    created_measurements = FlowMeasurementPredio.objects.bulk_create()

    
    print("-" * 50)
    print(f"Total de mediciones creadas: {len(created_measurements)}")
    
    
    for idx, medicion in enumerate(created_measurements, 1):
        print(f"Medición {idx}:")
        print(f"   ID: {medicion.id}")
        print(f"   Predio: {medicion.plot.plot_name}")
        print(f"   Dispositivo: {medicion.device.name}")
        print(f"   Caudal: {medicion.flow_rate} m³/s")
        print(f"   Timestamp: {medicion.timestamp}")
        print("-" * 50)
    
    return created_measurements


@pytest.fixture
def authenticated_admin_client(db, create_admin_user):
    """Crear cliente autenticado para admin."""
    client = APIClient()
    client.force_authenticate(user=create_admin_user)
    print("✅ Cliente de administrador autenticado")
    return client

@pytest.fixture
def authenticated_fincario_client(db, create_fincario_user):
    """Crear cliente autenticado para fincario."""
    client = APIClient()
    client.force_authenticate(user=create_fincario_user)
    print("✅ Cliente de fincario autenticado")
    return client


@pytest.mark.django_db
def test_admin_can_view_all_plot_consumption_history(
    authenticated_admin_client, 
    create_flow_measurements, 
    create_test_devices
):
    """
    Prueba que un administrador pueda ver el historial de consumo de todos los predios.
    """
    print("\n📋 Iniciando prueba: Administrador - Historial de Consumo de Todos los Predios")
    
    # Obtener todos los predios
    response = authenticated_admin_client.get("/api/caudal/flow-measurements/predio/listar")
    
    print(f"🔍 Código de respuesta: {response.status_code}")
    assert response.status_code == 200, f"❌ Error: {response.status_code}, Respuesta: {response.json()}"
    
    
    created_measurements = response.json()
    print(f"📊 Total de mediciones encontradas: {len(created_measurements)}")
    assert len(created_measurements) > 1, "❌ El administrador debería ver mediciones de varios predios"
    print("✅ Administrador puede ver historial de consumo de todos los predios")
   

@pytest.mark.django_db
def test_fincario_can_only_view_own_plot_consumption_history(
    authenticated_fincario_client, 
    create_flow_measurements, 
    create_test_devices,
    create_predios
):
    """
    Prueba que un fincario solo pueda ver el historial de consumo de sus propios predios.
    """
    print("\n📋 Iniciando prueba: Fincario - Historial de Consumo Solo de sus Predios")
    
    # Obtener los predios
    _, predio_fincario = create_predios

    # Solicitar todas las mediciones
    response = authenticated_fincario_client.get("/api/caudal/flow-measurements/predio/listar")
    
    print(f"🔍 Código de respuesta: {response.status_code}")
    assert response.status_code == 200, f"❌ Error: {response.status_code}, Respuesta: {response.json()}"
    
    created_measurements = response.json()
    
    print(f"📊 Total de mediciones encontradas: {len(created_measurements)}")

    assert len(created_measurements) > 0, "❌ El fincario debería ver al menos sus propias mediciones"
    
    # Verificar que todas las mediciones son de su predio
    for m in created_measurements:
        assert m["plot"] == predio_fincario.id_plot, "❌ Solo debe ver mediciones de su propio predio"

    # Intentar ver medición de otro predio debe ser denegado
    _, predio_admin = create_predios
    response_otro_predio = authenticated_fincario_client.get(f"/api/caudal/flow-measurements/predio/{predio_admin.id_plot}")
    
    print(f"🔒 Intento de acceso a predio ajeno - Código de respuesta: {response_otro_predio.status_code}")
    assert response_otro_predio.status_code == 403, "❌ No debería poder ver mediciones de otros predios"
    
    print("✅ Fincario solo puede ver historial de consumo de sus propios predios")

@pytest.mark.django_db
def test_plot_consumption_history_details(
    authenticated_admin_client, 
    create_flow_measurements, 
    create_test_devices,
    create_predios
):
    """
    Prueba los detalles del historial de consumo de un predio específico por un administrador.
    """
    print("\n📋 Iniciando prueba: Detalles del Historial de Consumo de Predio")
    
    predio_admin, _ = create_predios
    
    # Obtener mediciones de un predio específico
    response = authenticated_admin_client.get(f"/api/caudal/flow-measurements/predio/{predio_admin.id_plot}")
    
    print(f"🔍 Código de respuesta: {response.status_code}")
    assert response.status_code == 200, f"❌ Error: {response.status_code}, Respuesta: {response.json()}"
    
    created_measurements = response.json()
    print(f"📊 Total de mediciones encontradas: {len(created_measurements)}")
    assert len(created_measurements) > 0, "❌ Debe haber al menos una medición para el predio"
    

    for m in created_measurements:
        print(f"🌊 Medición - Caudal: {m['flow_rate']}, Timestamp: {m['timestamp']}")
        assert "plot" in m, "❌ La medición debe incluir información del predio"
        assert "device" in m, "❌ La medición debe incluir información del dispositivo"
        assert "timestamp" in m, "❌ La medición debe incluir marca de tiempo"
        assert "flow_rate" in m, "❌ La medición debe incluir el caudal"

    print("✅ Detalles del historial de consumo verificados correctamente")