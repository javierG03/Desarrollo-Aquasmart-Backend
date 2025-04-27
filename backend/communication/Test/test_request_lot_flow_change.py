import pytest
from django.urls import reverse
from rest_framework import status
from communication.request.models import FlowChangeRequest
from iot.models import IoTDevice, DeviceType  # Ajusta si el path es diferente
from plots_lots.models import Plot
from users.models import CustomUser, Otp

@pytest.mark.django_db
def test_user_can_request_flow_change(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    """
    ✅ Verifica que un usuario autenticado pueda solicitar un cambio de caudal
    para un dispositivo IoT asociado a su predio.
    """
    
    assert user_plot.owner == normal_user, "❌ El predio no pertenece al usuario"
    assert user_lot[1].plot == user_plot, "❌ El lote no pertenece al predio"

    
    # 🔐 Paso 3: Autenticación del usuario y obtención del token
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # 🔹 Paso 4: Construcción del payload
    url = reverse("flow-change-request")  # Asegúrate que este nombre está en urls.py
    
    payload = {
        "device": iot_device[0].iot_id,
        
        "requested_flow": 10.5,
        "lot": user_lot[0].pk
        
    }
    print(f"Payload enviado: {payload}")
    

    assert isinstance(payload["requested_flow"], float), "❌ El caudal debe ser tipo float"

    # 🔹 Paso 5: Realizar la solicitud POST
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    # 🔎 Paso 6: Validar respuesta del servidor
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌ Error esperado HTTP 201 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    assert "id" in response.data, "❌ La respuesta no incluye el ID de la solicitud creada"
    assert float(response.data["requested_flow"]) == 10.5, "❌ El caudal registrado no coincide"

    # 🔎 Paso 7: Verificar existencia del registro en la base de datos
    request = FlowChangeRequest.objects.get(id=response.data["id"])

    assert request.requested_flow == 10.5, "❌ El caudal registrado en la BD no coincide"
    assert request.plot == user_plot, "❌ El predio asociado en BD es incorrecto"
    assert request.user == normal_user, "❌ El usuario asignado a la solicitud es incorrecto"

    print("✅ Solicitud de cambio de caudal creada correctamente.")