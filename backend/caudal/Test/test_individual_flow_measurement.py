import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from dateutil import parser
from caudal.models import FlowMeasurementLote
from plots_lots.models import Plot, Lot, SoilType
from iot.models import IoTDevice, DeviceType
from django.contrib.auth import get_user_model

User = get_user_model()

# 🔹 FIXTURES

@pytest.fixture
def create_regular_user(db):
    """Crea un usuario regular."""
    return User.objects.create_user(
        document="123456789014",
        password="user123",
        first_name="Customer",
        last_name="User",
        email="customuser@gmail.com",
        phone="01234567891",
        is_staff=False
    )

@pytest.fixture
def create_other_user(db):
    """Crea otro usuario regular diferente."""
    return User.objects.create_user(
        document="987654321000",
        password="otheruser123",
        first_name="Another",
        last_name="User",
        email="otheruser@gmail.com",
        phone="09876543210",
        is_staff=False
    )

@pytest.fixture
def create_predio(db, create_regular_user):
    """Crea un predio asociado al usuario regular."""
    return Plot.objects.create(
        plot_name="Predio Usuario",
        owner=create_regular_user,
        latitud=2.0,
        longitud=2.0,
        plot_extension=200.0
    )

@pytest.fixture
def create_other_predio(db, create_other_user):
    """Crea un predio que pertenece a otro usuario."""
    return Plot.objects.create(
        plot_name="Predio Ajeno",
        owner=create_other_user,
        latitud=3.0,
        longitud=3.0,
        plot_extension=300.0
    )

@pytest.fixture
def create_soil_type(db):
    """Crea un tipo de suelo."""
    return SoilType.objects.create(name="Arcilloso")

@pytest.fixture
def create_lote(db, create_predio, create_soil_type):
    """Crea un lote en el predio del usuario regular."""
    return Lot.objects.create(plot=create_predio, soil_type=create_soil_type)

@pytest.fixture
def create_other_lote(db, create_other_predio, create_soil_type):
    """Crea un lote en un predio que no pertenece al usuario regular."""
    return Lot.objects.create(plot=create_other_predio, soil_type=create_soil_type)

@pytest.fixture
def create_device_type(db):
    """Crea un tipo de dispositivo."""
    return DeviceType.objects.create(name="Sensor de Flujo")

@pytest.fixture
def create_test_device(db, create_lote, create_device_type):
    """Crea un dispositivo IoT vinculado al lote del usuario."""
    return IoTDevice.objects.create(name="Sensor Usuario", id_lot=create_lote, device_type=create_device_type)

@pytest.fixture
def create_other_test_device(db, create_other_lote, create_device_type):
    """Crea un dispositivo IoT en un lote que no pertenece al usuario."""
    return IoTDevice.objects.create(name="Sensor Ajeno", id_lot=create_other_lote, device_type=create_device_type)

@pytest.fixture
def create_flow_measurements(db, create_test_device, create_lote):
    
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    seven_months_ago = timezone.now() - timezone.timedelta(days=210)

    FlowMeasurementLote.objects.bulk_create([

        FlowMeasurementLote(lot=create_lote, device=create_test_device, timestamp=six_months_ago + timezone.timedelta(days=1), flow_rate=12.5),
        FlowMeasurementLote(lot=create_lote, device=create_test_device, timestamp=timezone.now(), flow_rate=15.5),
        FlowMeasurementLote(lot=create_lote, device=create_test_device, timestamp=seven_months_ago, flow_rate=10.2),
    ])


@pytest.fixture
def authenticated_client(db, create_regular_user):
    """Autentica al usuario regular en el cliente de pruebas."""
    client = APIClient()
    client.force_authenticate(user=create_regular_user)
    return client

@pytest.fixture
def authenticated_other_client(db, create_other_user):
    """Autentica a otro usuario diferente."""
    client = APIClient()
    client.force_authenticate(user=create_other_user)
    return client

# 🔹 TESTS

@pytest.mark.django_db
def test_user_can_view_own_plot_flow_history(authenticated_client, create_flow_measurements, create_test_device):
    
    device_user = create_test_device
    lote_id = device_user.id_lot.id_lot

    response = authenticated_client.get(f"/api/caudal/flow-measurements/lote/{lote_id}")
    
    assert response.status_code == 200, f"Error: {response.status_code}, Respuesta: {response.json()}"

    measurements = response.json()
    print(f"📊 Mediciones obtenidas: {measurements}")



@pytest.mark.django_db
def test_user_cannot_view_other_plot_flow_history(authenticated_client, create_other_test_device):
    """Verifica que el usuario no pueda ver el historial de consumo de otro predio."""
    device_other = create_other_test_device
    lote_id = device_other.id_lot.id_lot

    response = authenticated_client.get(f"/api/caudal/flow-measurements/lote/{lote_id}")
    
    assert response.status_code == 403, f"❌ El usuario pudo acceder a un predio ajeno. Respuesta: {response.json()}"

@pytest.mark.django_db
def test_other_user_cannot_view_user_plot_flow_history(authenticated_other_client, create_test_device):
    """Verifica que otro usuario no pueda ver el historial del usuario original."""
    device_user = create_test_device
    lote_id = device_user.id_lot.id_lot

    response = authenticated_other_client.get(f"/api/caudal/flow-measurements/lote/{lote_id}")
    
    assert response.status_code == 403, f"❌ Otro usuario pudo acceder a un predio ajeno. Respuesta: {response.json()}"

