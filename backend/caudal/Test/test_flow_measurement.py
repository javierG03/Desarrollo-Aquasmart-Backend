import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import Group
from users.models import Otp
from iot.models import IoTDevice, DeviceType
from caudal.models import FlowMeasurement
from django.utils import timezone


@pytest.fixture
def api_client():
    """Devuelve un cliente de prueba para hacer solicitudes a la API."""
    return APIClient()


@pytest.fixture
def ensure_groups_exist(db):
    """Crea los grupos necesarios en la base de datos de prueba."""
    Group.objects.get_or_create(id=1, name="Administrador")
    Group.objects.get_or_create(id=2, name="Usuario Normal")


@pytest.fixture
def create_admin_user(db, ensure_groups_exist):
    """Crea un usuario administrador y lo asigna al grupo correspondiente."""
    User = get_user_model()
    user = User.objects.create_user(
        document="123456789012",
        first_name="Admin",
        last_name="User",
        email="admin@gmail.com",
        phone="1234567890",
        address="123 Admin St",
        password="SecurePass123@",
        is_active=True,
        is_registered=True,
        is_staff=True
    )
    group = Group.objects.get(name="Administrador")
    user.groups.add(group)
    user.save()
    return user


@pytest.fixture
def create_regular_user(db, ensure_groups_exist):
    """Crea un usuario normal y lo asigna al grupo correspondiente."""
    User = get_user_model()
    user = User.objects.create_user(
        document="987654321098",
        first_name="Regular",
        last_name="User",
        email="regular@gmail.com",
        phone="0987654321",
        address="123 Regular St",
        password="SecurePass123@",
        is_active=True,
        is_registered=True,
        is_staff=False
    )
    group = Group.objects.get(name="Usuario Normal")
    user.groups.add(group)
    user.save()
    return user


@pytest.fixture
def create_test_device(db):
    """Crea un dispositivo IoT de prueba con un tipo de dispositivo válido."""
    device_type = DeviceType.objects.create(name="Sensor de Flujo")
    return IoTDevice.objects.create(
        iot_id="01-0001",
        name="Test IoT Device",
        device_type=device_type,
        is_active=True,
        characteristics="Sensor de flujo de agua"
    )


@pytest.fixture
def create_flow_measurements(db, create_test_device):
    """Crea múltiples mediciones de caudal para simular un historial de consumo."""
    FlowMeasurement.objects.bulk_create([
        FlowMeasurement(device=create_test_device, timestamp=timezone.now(), flow_rate=15.5),
        FlowMeasurement(device=create_test_device, timestamp=timezone.now() - timezone.timedelta(days=1), flow_rate=14.8),
        FlowMeasurement(device=create_test_device, timestamp=timezone.now() - timezone.timedelta(days=2), flow_rate=16.2),
    ])



@pytest.fixture
def authenticated_client(api_client, create_admin_user):
    """Autentica al usuario administrador y devuelve un cliente con sesión activa."""
    return authenticate_user(api_client, create_admin_user)


@pytest.fixture
def authenticated_regular_client(api_client, create_regular_user):
    """Autentica al usuario normal y devuelve un cliente con sesión activa."""
    return authenticate_user(api_client, create_regular_user)


def authenticate_user(api_client, user):
    """Autentica un usuario en la API y configura su sesión."""
    login_url = reverse("login")
    otp_url = reverse("validate-otp")

    # 📌 1️⃣ Iniciar sesión para generar OTP
    login_data = {"document": user.document, "password": "SecurePass123@"}
    login_response = api_client.post(login_url, login_data)
    assert login_response.status_code == 200, f"❌ Error en login: {login_response.data}"

    # 📌 2️⃣ Obtener OTP de la base de datos
    otp_instance = Otp.objects.filter(user=user, is_login=True).first()
    assert otp_instance, "❌ No se generó OTP en la base de datos"

    # 📌 3️⃣ Validar el OTP
    otp_data = {"document": user.document, "otp": otp_instance.otp}
    otp_response = api_client.post(otp_url, otp_data)
    assert otp_response.status_code == 200, f"❌ Error al validar OTP: {otp_response.data}"
    assert "token" in otp_response.data, "❌ No se recibió un token"

    # 📌 4️⃣ Configurar el token en el cliente autenticado
    token = otp_response.data["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    return api_client


@pytest.mark.django_db
@pytest.mark.parametrize("user_fixture, user_creator, expected_status, role", [
    ("authenticated_client", "create_admin_user", 200, "Administrador"),  # Admin debe acceder correctamente
    ("authenticated_regular_client", "create_regular_user", 403, "Usuario Normal"),  # Usuario normal NO debe acceder
])
def test_user_flow(request, user_fixture, user_creator, expected_status, role, create_flow_measurements):
    """
    Prueba que un usuario pueda (o no) iniciar sesión, acceder y visualizar el historial de consumo general.
    """

    print(f"\n🔹 **Probando acceso con usuario {role}**")

    # 📌 1️⃣ Obtener el cliente autenticado y el usuario desde los fixtures
    client = request.getfixturevalue(user_fixture)
    user = request.getfixturevalue(user_creator)

    # 📌 2️⃣ Verificar inicio de sesión correcto
    assert user is not None, f"❌ Usuario ({role}) no se creó correctamente."
    assert user.is_authenticated, f"❌ Falló el inicio de sesión para {role}"
    print(f"✅ El usuario ({role}) pudo iniciar sesión correctamente.")

    # 📌 3️⃣ Verificar el grupo y permisos
    user_groups = user.groups.all()
    print(f"👥 Grupos del usuario: {[g.name for g in user_groups]}")

    user_permissions = user.get_all_permissions()
    print(f"🔑 Permisos asignados al usuario: {user_permissions}")

    # 📌 4️⃣ Intentar acceder al historial de consumo
    history_url = reverse("flowmeasurement-list")
    response = client.get(history_url)

   # 📌 5️⃣ Verificar el acceso correcto o la denegación esperada
    assert response.status_code == expected_status, f"❌ Código {response.status_code} en lugar de {expected_status}"

# 📌 6️⃣ Si el usuario tiene acceso, mostramos las mediciones
    if response.status_code == 200:
        print(f"✅ El usuario ({role}) pudo acceder al historial de consumo general.")

    # ✅ Verificamos que `response.data` sea una lista antes de iterar
        if isinstance(response.data, list):
            print(f"📊 Se encontraron {len(response.data)} registros en el historial de consumo.")
            for record in response.data:
                print(f"   📅 Fecha: {record.get('timestamp', 'N/A')} | 💧 Caudal: {record.get('flow_rate', 'N/A')} L/s")
        else:
            print(f"🚨 Respuesta inesperada: {response.data}")
            pytest.fail(f"❌ Se esperaba una lista, pero se recibió: {type(response.data)}")

    elif response.status_code == 403:
        print(f"🚫 Acceso denegado para {role}: {response.data}")

