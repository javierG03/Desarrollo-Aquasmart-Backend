import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

# Modelos necesarios para las pruebas
from communication.request.models import FlowActivationRequest, FlowChangeRequest, FlowCancelRequest
from iot.models import IoTDevice, DeviceType, VALVE_4_ID, VALVE_48_ID
from plots_lots.models import Plot, Lot, SoilType, CropType
from users.models import CustomUser, PersonType, Otp

# Autenticación
from rest_framework.authtoken.models import Token


@pytest.mark.django_db
def test_user_can_request_flow_activation(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device):
    """
    ✅ RF63: Verifica que un usuario pueda solicitar la activación de caudal para un lote.
    HU01-HU07: Acceso al módulo y visualización de la opción
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot  
    valvula4, _, _, _ = iot_device  # Válvula de 4" creada en fixture
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # 🔹 Preparar el payload para la solicitud
    url = reverse("flow-activation-request")
    payload = {
        "lot": lote.id_lot,
        "requested_flow": 5.5,  # Solicitar un caudal de 5.5 L/s
        "observations": "Necesito activar el riego para mi cultivo"
    }
    
    print(f"Payload enviado: {payload}")
    
    # 🔹 Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar respuesta del servidor
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌ Error al crear solicitud de activación de caudal: {response.data}. "
        f"Código esperado: {status.HTTP_201_CREATED}, obtenido: {response.status_code}"
    )
    
    # 🔎 Verificar que la solicitud se guardó en la BD
    assert FlowActivationRequest.objects.filter(
        lot=lote, 
        requested_flow=5.5,
        status='pendiente'
    ).exists(), "❌ La solicitud no se guardó correctamente en la base de datos"
    
    print("✅ RF63-HU01-HU07: Solicitud de activación de caudal creada correctamente")


@pytest.mark.django_db
def test_cannot_request_flow_activation_for_active_flow(api_client, normal_user, login_and_validate_otp, user_lot, iot_device):
    """
    ✅ RF63-HU19: Verificar que no se pueda solicitar activación cuando el caudal ya está activo.
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal activo (mayor que 0)
    # Esto prueba la HU19 - usuario intenta activar un caudal ya activo
    valvula4.actual_flow = 4.5  # Caudal ya activo
    valvula4.save()
    
    # 🔹 Preparar el payload para la solicitud
    url = reverse("flow-activation-request")
    payload = {
        "lot": lote.id_lot,
        "requested_flow": 6.0,
        "observations": "Solicitud que debería fallar"
    }
    
    print(f"Payload enviado: {payload}")
    
    # 🔹 Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud debería ser rechazada pero se obtuvo código {response.status_code}"
    )
    
    # Verificar que el mensaje de error es el esperado
    assert "El caudal del lote ya está activo" in str(response.data), (
        f"❌ El mensaje de error no coincide con el esperado: {response.data}"
    )
    
    print("✅ RF63-HU19: Validación correcta cuando el caudal ya está activo")


@pytest.mark.django_db
def test_cannot_request_flow_activation_with_pending_request(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device):
    """
    ✅ RF63-HU16/HU17: Verificar que no se pueda solicitar activación cuando ya existe una solicitud pendiente.
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener el lote y la válvula del conftest
    lote, _, _  = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # Crear una solicitud pendiente para simular una solicitud en curso (HU16/HU17)
    FlowActivationRequest.objects.create(
        user=normal_user,
        lot=lote,
        plot=user_plot,  # Asignar el predio también
        requested_flow=5.5,
        status='pendiente'
    )
    
    # 🔹 Preparar el payload para una nueva solicitud
    url = reverse("flow-activation-request")
    payload = {
        "lot": lote.id_lot,
        "requested_flow": 6.0,
        "observations": "Solicitud que debería fallar"
    }
    
    print(f"Payload enviado: {payload}")
    
    # 🔹 Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud debería ser rechazada pero se obtuvo código {response.status_code}"
    )
    
    # Verificar que el mensaje de error es el esperado
    assert "solicitud de activación de caudal en curso" in str(response.data).lower(), (
        f"❌ El mensaje de error no coincide con el esperado: {response.data}"
    )
    
    print("✅ RF63-HU16/HU17: Validación correcta cuando ya existe una solicitud pendiente")


@pytest.mark.django_db
def test_validate_flow_range(api_client, normal_user, login_and_validate_otp, user_lot, iot_device):
    """
    ✅ RF63: Validar que el caudal solicitado esté dentro del rango permitido (1-11.7 L/s).
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # 🔹 Caso 1: Caudal por debajo del mínimo (menos de 1 L/s)
    url = reverse("flow-activation-request")
    payload_below = {
        "lot": lote.id_lot,
        "requested_flow": 0.5,  # Menos del mínimo
        "observations": "Caudal demasiado bajo"
    }
    
    print(f"Caso 1 - Payload enviado (caudal bajo): {payload_below}")
    response_below = client.post(url, payload_below, format="json")
    print(f"Respuesta caso 1 ({response_below.status_code}): {response_below.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response_below.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud con caudal bajo debería ser rechazada pero se obtuvo código {response_below.status_code}"
    )
    
    # 🔹 Caso 2: Caudal por encima del máximo (más de 11.7 L/s)
    payload_above = {
        "lot": lote.id_lot,
        "requested_flow": 12.0,  # Más del máximo
        "observations": "Caudal demasiado alto"
    }
    
    print(f"Caso 2 - Payload enviado (caudal alto): {payload_above}")
    response_above = client.post(url, payload_above, format="json")
    print(f"Respuesta caso 2 ({response_above.status_code}): {response_above.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response_above.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud con caudal alto debería ser rechazada pero se obtuvo código {response_above.status_code}"
    )
    
    # 🔹 Caso 3: Caudal dentro del rango permitido
    payload_valid = {
        "lot": lote.id_lot,
        "requested_flow": 10.0,  # Dentro del rango
        "observations": "Caudal válido"
    }
    
    print(f"Caso 3 - Payload enviado (caudal válido): {payload_valid}")
    response_valid = client.post(url, payload_valid, format="json")
    print(f"Respuesta caso 3 ({response_valid.status_code}): {response_valid.data}")
    
    # 🔎 Validar que la solicitud sea aceptada
    assert response_valid.status_code == status.HTTP_201_CREATED, (
        f"❌ La solicitud con caudal válido debería ser aceptada pero se obtuvo código {response_valid.status_code}"
    )
    
    print("✅ RF63: Validación correcta del rango de caudal solicitado (1-11.7 L/s)")


@pytest.mark.django_db
def test_cannot_request_flow_activation_for_inactive_lot(api_client, normal_user, login_and_validate_otp, inactive_user_plot, device_type, soil_type, crop_type):
    """
    ✅ RF63: Verificar que no se pueda solicitar activación para un lote inactivo.
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener tipo de dispositivo - válvula 4" del conftest
    _, _, _, _, _, _, valve_type = device_type
    
    # Crear lote inactivo
    inactive_lot = Lot.objects.create(
        plot=inactive_user_plot,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Cultivo inactivo",
        crop_variety="Variedad X",
        is_activate=False  # Lote inactivo - para probar restricción
    )
    
    # Crear válvula para el lote inactivo
    inactive_valve = IoTDevice.objects.create(
        device_type=valve_type,
        name="Válvula lote inactivo",
        id_plot=inactive_user_plot,
        id_lot=inactive_lot,
        is_active=True,
        actual_flow=0
    )
    
    # 🔹 Preparar el payload para la solicitud
    url = reverse("flow-activation-request")
    payload = {
        "lot": inactive_lot.id_lot,
        "requested_flow": 5.5,
        "observations": "Solicitud para lote inactivo"
    }
    
    print(f"Payload enviado (lote inactivo): {payload}")
    
    # 🔹 Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud para lote inactivo debería ser rechazada pero se obtuvo código {response.status_code}"
    )
    
    # Verificar que el mensaje de error menciona que el lote está inhabilitado
    assert "inhabilitado" in str(response.data).lower(), (
        f"❌ El mensaje de error no menciona que el lote está inhabilitado: {response.data}"
    )
    
    print("✅ RF63: Validación correcta cuando el lote está inactivo")


@pytest.mark.django_db
def test_admin_can_approve_flow_activation_request(api_client, admin_user, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device):
    """
    ✅ RF63: Verificar que un administrador pueda aprobar una solicitud de activación de caudal.
    """
    # Obtener el lote y la válvula del conftest
    lote, _, _  = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # Crear una solicitud pendiente
    request = FlowActivationRequest.objects.create(
        user=normal_user,
        lot=lote,
        plot=user_plot,
        requested_flow=7.5,
        status='pendiente'
    )
    
    # 🔐 Login como administrador
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    
    # 🔹 Preparar el payload para aprobar la solicitud
    url = reverse("flow-activation-request-status", args=[request.id])
    payload = {
        "status": "aprobada"
    }
    
    print(f"Payload para aprobación: {payload}")
    
    # 🔹 Realizar la solicitud PATCH
    response = client.patch(url, payload, format="json")
    print(f"Respuesta aprobación ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea aceptada
    assert response.status_code == status.HTTP_200_OK, (
        f"❌ La aprobación debería ser aceptada pero se obtuvo código {response.status_code}: {response.data}"
    )
    
    # Verificar que el estado se actualizó en la BD
    request.refresh_from_db()
    assert request.status == 'aprobada', f"❌ El estado de la solicitud no se actualizó a 'aprobada': {request.status}"
    
    # Verificar que el caudal se aplicó en la válvula
    valvula4.refresh_from_db()
    assert valvula4.actual_flow == 7.5, f"❌ El caudal no se actualizó en la válvula: {valvula4.actual_flow} != 7.5"
    
    print("✅ RF63-HU25: Administrador puede aprobar solicitud de activación de caudal")


@pytest.mark.django_db
def test_admin_can_reject_flow_activation_request(api_client, admin_user, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device):
    """
    ✅ RF63: Verificar que un administrador pueda rechazar una solicitud de activación de caudal.
    """
    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # Crear una solicitud pendiente para simular proceso de rechazo
    request = FlowActivationRequest.objects.create(
        user=normal_user,
        lot=lote,
        plot=user_plot,
        requested_flow=7.5,
        status='pendiente'
    )
    
    # 🔐 Login como administrador
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    
    # 🔹 Preparar el payload para rechazar la solicitud
    url = reverse("flow-activation-request-status", args=[request.id])
    payload = {
        "status": "rechazada"
    }
    
    print(f"Payload para rechazo: {payload}")
    
    # 🔹 Realizar la solicitud PATCH
    response = client.patch(url, payload, format="json")
    print(f"Respuesta rechazo ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea aceptada
    assert response.status_code == status.HTTP_200_OK, (
        f"❌ El rechazo debería ser procesado correctamente pero se obtuvo código {response.status_code}: {response.data}"
    )
    
    # Verificar que el estado se actualizó en la BD
    request.refresh_from_db()
    assert request.status == 'rechazada', f"❌ El estado de la solicitud no se actualizó a 'rechazada': {request.status}"
    
    # Verificar que el caudal NO cambió (sigue en 0)
    valvula4.refresh_from_db()
    assert valvula4.actual_flow == 0, f"❌ El caudal no debió actualizarse pero cambió: {valvula4.actual_flow} != 0"
    
    print("✅ RF63: Administrador puede rechazar solicitud de activación de caudal")


@pytest.mark.django_db
def test_other_user_cannot_request_flow_activation(api_client, admin_user, normal_user, login_and_validate_otp, user_plot, user_lot):
    """
    ✅ RF63: Verificar que un usuario no pueda solicitar activación de caudal para lotes que no le pertenecen.
    HU12-13: Validación del usuario propietario
    """
    # Crear un usuario diferente al dueño del lote
    person_type = PersonType.objects.first()
    
    other_user = CustomUser.objects.create_user(
        document="333444555",
        first_name="Otro",
        last_name="Usuario",
        email="otro@example.com",
        phone="3001112233",
        password="OtroPass123@",
        person_type=person_type,
        is_registered=True
    )
    
    # 🔐 Login como el otro usuario
    client = login_and_validate_otp(api_client, other_user, "OtroPass123@")
    
    # Obtener el lote del primer usuario
    lote, _, _ = user_lot
    
    # 🔹 Preparar el payload para la solicitud
    url = reverse("flow-activation-request")
    payload = {
        "lot": lote.id_lot,
        "requested_flow": 5.5,
        "observations": "Solicitud que debería fallar"
    }
    
    print(f"Payload enviado por usuario no propietario: {payload}")
    
    # 🔹 Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud debería ser rechazada pero se obtuvo código {response.status_code}"
    )
    
    # Verificar que el mensaje de error sea por problema de propiedad o por falta de válvula
    expected_errors = [
        "Solo el dueño del predio puede realizar una solicitud",
        "El lote no tiene una válvula 4\" asociada"
    ]
    
    error_found = any(error in str(response.data) for error in expected_errors)
    assert error_found, (
        f"❌ El mensaje de error no indica problema de propiedad o falta de válvula: {response.data}"
    )
    
    print("✅ RF63-HU12-13: Usuario no puede solicitar activación para lotes que no le pertenecen")


@pytest.mark.django_db
def test_required_fields_validation(api_client, normal_user, login_and_validate_otp, user_lot, iot_device):
    """
    ✅ RF63: Verificar que se validen los campos requeridos en el formulario.
    HU8-9: Validación de los datos ingresados
    """
    # 🔐 Login como usuario normal
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # Caso 1: Solicitud sin lote
    url = reverse("flow-activation-request")
    payload_missing_lot = {
        "requested_flow": 5.5,
        "observations": "Falta el lote"
    }
    
    print(f"Caso 1 - Payload sin lote: {payload_missing_lot}")
    response_missing_lot = client.post(url, payload_missing_lot, format="json")
    print(f"Respuesta caso 1 ({response_missing_lot.status_code}): {response_missing_lot.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response_missing_lot.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud sin lote debería ser rechazada pero se obtuvo código {response_missing_lot.status_code}"
    )
    
    # Caso 2: Solicitud sin caudal solicitado
    payload_missing_flow = {
        "lot": lote.id_lot,
        "observations": "Falta el caudal"
    }
    
    print(f"Caso 2 - Payload sin caudal: {payload_missing_flow}")
    response_missing_flow = client.post(url, payload_missing_flow, format="json")
    print(f"Respuesta caso 2 ({response_missing_flow.status_code}): {response_missing_flow.data}")
    
    # 🔎 Validar que la solicitud sea rechazada
    assert response_missing_flow.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ La solicitud sin caudal debería ser rechazada pero se obtuvo código {response_missing_flow.status_code}"
    )
    
    # Caso 3: Solicitud con todos los campos obligatorios
    payload_valid = {
        "lot": lote.id_lot,
        "requested_flow": 5.5,
        "observations": "Con todos los campos"
    }
    
    print(f"Caso 3 - Payload válido: {payload_valid}")
    response_valid = client.post(url, payload_valid, format="json")
    print(f"Respuesta caso 3 ({response_valid.status_code}): {response_valid.data}")
    
    # 🔎 Validar que la solicitud sea aceptada
    assert response_valid.status_code == status.HTTP_201_CREATED, (
        f"❌ La solicitud válida debería ser aceptada pero se obtuvo código {response_valid.status_code}"
    )
    
    print("✅ RF63-HU8-9: Validación de campos requeridos funciona correctamente")


@pytest.mark.django_db
def test_non_admin_cannot_approve_request(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device):
    """
    ✅ RF63: Verificar que un usuario normal no pueda aprobar o rechazar solicitudes.
    """
    # Obtener el lote y la válvula del conftest
    lote, _, _ = user_lot
    valvula4, _, _, _ = iot_device
    
    # Asegurar que la válvula tiene caudal en 0 (cancelado)
    valvula4.actual_flow = 0
    valvula4.save()
    
    # Crear una solicitud pendiente
    request = FlowActivationRequest.objects.create(
        user=normal_user,
        lot=lote,
        plot=user_plot,
        requested_flow=7.5,
        status='pendiente'
    )
    
    # 🔐 Login como usuario normal (no administrador)
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    
    # 🔹 Preparar el payload para aprobar la solicitud
    url = reverse("flow-activation-request-status", args=[request.id])
    payload = {
        "status": "aprobada"
    }
    
    print(f"Payload para aprobación (usuario normal): {payload}")
    
    # 🔹 Realizar la solicitud PATCH
    response = client.patch(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    # 🔎 Validar que se deniega la acción
    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"❌ La acción debería ser denegada pero se obtuvo código {response.status_code}"
    )
    
    # Verificar que el estado no cambió en la BD
    request.refresh_from_db()
    assert request.status == 'pendiente', (
        f"❌ El estado de la solicitud no debería cambiar pero es: {request.status}"
    )
    
    print("✅ RF63: Usuario normal no puede aprobar solicitudes")