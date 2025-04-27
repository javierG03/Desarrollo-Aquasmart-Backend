import pytest
from django.urls import reverse
from rest_framework import status
from communication.request.models import FlowChangeRequest
from iot.models import IoTDevice, DeviceType  # Ajusta si el path es diferente
from plots_lots.models import Plot
from users.models import CustomUser, Otp

@pytest.mark.django_db
def test_user_can_request_flow_cancellation(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    """
    ✅ Verifica que un usuario pueda solicitar la cancelación de un cambio de caudal activo.
    """
    

    # 🔐 Login
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")


    url = reverse("flow-change-request")  # Asegúrate que este nombre está en urls.py
    
    flow_request = {
        "device": iot_device[0].iot_id,
        
        "requested_flow": 10.5,
        "lot": user_lot[0].pk
        
    }
    print(f"Payload enviado: {flow_request}")
    

    assert isinstance(flow_request["requested_flow"], float), "❌ El caudal debe ser tipo float"

    # 🔹 Paso 5: Realizar la solicitud POST
    response = client.post(url, flow_request, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    # 🔎 Paso 6: Validar respuesta del servidor
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌ Error esperado HTTP 201 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )

    assert user_plot.owner == normal_user, "❌ El predio no pertenece al usuario"
    assert user_lot[0].plot == user_plot, "❌ El lote no pertenece al predio"

    # 🔹 Hacer solicitud de cancelación
    url = reverse("flow-cancel-request")  # Asegúrate que esté correctamente en tus URLs
    payload = {
        "cancel_type": "temporal",
        "lot": user_lot[0].pk,
        "observations": "No necesito el caudal adicional por ahora"
    }

    response = client.post(url, payload, format="json")

    # 🔎 Validaciones
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌ Se esperaba HTTP 200 pero se obtuvo {response.status_code}. Respuesta: {response.data}"
    )

    print("✅ Solicitud de cancelación de caudal realizada correctamente.")