import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from caudal.models import FlowMeasurementLote  # ✅ Importación corregida
from plots_lots.models import Plot, Lot, SoilType, CropType
from iot.models import IoTDevice, DeviceType
from datetime import datetime
from dateutil import parser  
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()

# 🔹 FIXTURES

@pytest.fixture
def create_admin_user(db):
    return User.objects.create_user(document="123456789012", first_name="admin", last_name="User", 
                                    email="adminuser@gmail.com", phone="01234567890", password="admin123", 
                                    is_staff=True)

@pytest.fixture
def create_regular_user(db):
    return User.objects.create_user(document="123456789014", password="user123", first_name="Customer", 
                                    last_name="User", email="customuser@gmail.com", phone="01234567891", 
                                    is_staff=False)

@pytest.fixture
def create_predios(db, create_admin_user, create_regular_user):
    predio_admin = Plot.objects.create(plot_name="Predio Admin", owner=create_admin_user, 
                                       latitud=1.0, longitud=1.0, plot_extension=100.0)
    predio_user = Plot.objects.create(plot_name="Predio Usuario", owner=create_regular_user, 
                                      latitud=2.0, longitud=2.0, plot_extension=200.0)
    return predio_admin, predio_user

@pytest.fixture
def create_soil_type(db):
    """Crea un tipo de suelo para los lotes."""
    return SoilType.objects.create(name="Arcilloso")

@pytest.fixture
def create_crop_type(db):
    return CropType.objects.create(name="Maíz")

@pytest.fixture
def create_lotes(db, create_predios, create_soil_type):
    """Crea lotes asociados a los predios con un tipo de suelo."""
    predio_admin, predio_user = create_predios
    soil_type = create_soil_type  # ✅ Quita los paréntesis

    lote_admin = Lot.objects.create(plot=predio_admin, soil_type=soil_type)
    lote_user = Lot.objects.create(plot=predio_user, soil_type=soil_type)

    return lote_admin, lote_user

@pytest.fixture
def create_device_type(db):
    """Crea un tipo de dispositivo."""
    return DeviceType.objects.create(name="Sensor de Flujo")

@pytest.fixture
def create_test_device(db, create_lotes, create_device_type):
    """Crea un dispositivo IoT vinculado a un lote con un tipo de dispositivo."""
    lote_admin, lote_user = create_lotes
    device_type = create_device_type  # ✅ Llamar correctamente la función

    device_admin = IoTDevice.objects.create(name="Sensor Admin", id_lot=lote_admin, device_type=device_type)
    device_user = IoTDevice.objects.create(name="Sensor Usuario", id_lot=lote_user, device_type=device_type)

    return device_admin, device_user




@pytest.fixture
def create_flow_measurements(db, create_test_device, create_lotes):
    """Crea mediciones de caudal para los lotes."""
    lote_admin, lote_user = create_lotes
    device_admin, device_user = create_test_device

    now = timezone.now()

    FlowMeasurementLote.objects.bulk_create([
        
        FlowMeasurementLote(lot=lote_admin, device=device_admin, timestamp=now - timezone.timedelta(days=150), flow_rate=15.5),
        FlowMeasurementLote(lot=lote_user, device=device_user, timestamp=now - timezone.timedelta(days=210), flow_rate=14.8),
    ])

    print(f"📊 Mediciones creadas:")
    for m in FlowMeasurementLote.objects.all():
        print(f"Lote: {m.lot.id_lot}, Fecha: {m.timestamp}, Flow Rate: {m.flow_rate}")

@pytest.fixture
def authenticated_admin_client(db, create_admin_user):
    client = APIClient()
    client.force_authenticate(user=create_admin_user)
    return client


@pytest.fixture
def authenticated_regular_client(db, create_regular_user):
    client = APIClient()
    client.force_authenticate(user=create_regular_user)  # ✅ Usar force_authenticate en lugar de force_login
    return client

@pytest.mark.django_db
def test_admin_can_view_all_flow_measurements(authenticated_admin_client, create_flow_measurements, create_test_device):
    print(f"🔑 Usuario autenticado: {authenticated_admin_client.handler._force_user}")

    device_admin, device_user = create_test_device

    lote_admin_id = device_admin.id_lot.id_lot # Usa el ID real del lote
    lote_user_id = device_user.id_lot.id_lot  # Usa el ID real del lote

    print(f"🔗 URL Probada: /api/caudal/flow-measurements/lote/{lote_admin_id}")

    print(f"📊 Total mediciones en la BD: {FlowMeasurementLote.objects.count()}")
    for measurement in FlowMeasurementLote.objects.all():
        print(f"Lote: {measurement.lot.id_lot}, Flow Rate: {measurement.flow_rate}")

    print(f"📌 ID real del lote: {lote_admin_id}")

    response = authenticated_admin_client.get(f"/api/caudal/flow-measurements/lote/{lote_admin_id}")
    print(f"🔍 Todas las mediciones: {response.json()}")

    assert response.status_code == 200, f"Error: {response.status_code}, Respuesta: {response.json()}"
    assert len(response.json()) > 0

    


@pytest.mark.django_db
def test_regular_user_can_only_view_own_flow_measurements(authenticated_regular_client, create_flow_measurements, create_test_device):
    """
    Prueba que un usuario normal solo pueda ver sus propias mediciones y NO las de otros.
    """
    print("\n📋 Iniciando prueba: Usuario Normal - Ver solo sus propias mediciones")

    # 📌 Obtener dispositivos de prueba
    device_admin, device_user = create_test_device

    lote_admin_id = device_admin.id_lot.id_lot  # Lote del admin
    lote_user_id = device_user.id_lot.id_lot  # Lote del usuario normal

    print(f"🔗 URL Probada (Lote Usuario): /api/caudal/flow-measurements/lote/{lote_user_id}")
    print(f"🔗 URL Probada (Lote Admin): /api/caudal/flow-measurements/lote/{lote_admin_id}")

    # 📌 Verificar propietarios
    print(f"👤 Propietario del lote usuario: {device_user.id_lot.plot.owner.email}")
    print(f"👤 Propietario del lote admin: {device_admin.id_lot.plot.owner.email}")

    # 📌 1️⃣ Intentar ver las mediciones de su propio lote
    response_own = authenticated_regular_client.get(f"/api/caudal/flow-measurements/lote/{lote_user_id}")
    print(f"🔍 Código de respuesta (propias mediciones): {response_own.status_code}")
    
    assert response_own.status_code == 200, f"❌ Error inesperado al ver mediciones propias: {response_own.json()}"
    
    own_measurements = response_own.json()
    print(f"📊 Mediciones propias encontradas: {len(own_measurements)}")
    assert len(own_measurements) > 0, "❌ No se encontraron mediciones para el usuario normal"

    for record in own_measurements:
        print(f"   📅 Fecha: {record.get('timestamp', 'N/A')} | 💧 Caudal: {record.get('flow_rate', 'N/A')} L/s")
        assert record["lot"] == lote_user_id, "❌ Se encontraron mediciones de otro lote"

    print("✅ Usuario normal puede ver SOLO su historial de consumo correctamente.")

    # 📌 2️⃣ Intentar ver las mediciones del administrador (NO debería poder)
    response_forbidden = authenticated_regular_client.get(f"/api/caudal/flow-measurements/lote/{lote_admin_id}")
    print(f"🚫 Código de respuesta (intento de ver mediciones ajenas): {response_forbidden.status_code}")

    assert response_forbidden.status_code == 403, f"❌ El usuario normal NO debería ver mediciones del admin, pero recibió {response_forbidden.status_code}"
    print("✅ Se denegó correctamente el acceso a mediciones de otro usuario.")

    print("\n🎯 Test completado exitosamente.")
