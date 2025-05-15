import pytest
from django.urls import reverse
from rest_framework import status
from communication.requests.models import FlowRequest
from iot.models import IoTDevice, DeviceType  # Ajusta si el path es diferente
from plots_lots.models import Plot, Lot
from users.models import CustomUser, Otp



@pytest.mark.django_db
def test_valid_flow_change_request(api_client, normal_user, login_and_validate_otp, user_plot, user_lot,  iot_device ,device_type):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    

    url = reverse("flow-request-create")
    payload = {
        "flow_request_type" : "Cambio de Caudal",
        "lot": user_lot[0].pk,
        "type": "Solicitud",
        "requested_flow": 3.5,
        "observations": "Cambio por temporada"
    }
    print(f"Payload enviado: {payload}")

    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    assert response.status_code == 201, f"❌ Se esperaba 201, se recibió {response.status_code} - {response.data}"
    print("✅ Solicitud de cambio de caudal enviada correctamente.")


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
    url = reverse("flow-request-create")  # Asegúrate que este nombre está en urls.py
    
    payload = {        
        "requested_flow": 10.5,
        "lot": user_lot[0].pk,
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal"
        
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
    request = FlowRequest.objects.get(id=response.data["id"])

    assert request.requested_flow == 10.5, "❌ El caudal registrado en la BD no coincide"
    assert request.lot == user_lot[0], "❌ El lote asociado en BD es incorrecto"
    assert request.type == "Solicitud", "❌ El tipo de solicitud no es correcto"
    assert request.flow_request_type == "Cambio de Caudal", "❌ El tipo de solicitud no es correcto"
    assert request.status == "Pendiente", "❌ El estado de la solicitud no es correcto"
    

    print("✅ Solicitud de cambio de caudal creada correctamente.")



@pytest.mark.django_db
def test_user_cannot_request_flow_change_on_lot_with_pending_request(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    url = reverse("flow-request-create")
    payload = {
        "requested_flow": 10.5,
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal",
        "lot": user_lot[0].pk
    }
    print(f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌ Se esperaba HTTP 201 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    print ("✅ Solicitud de cambio de caudal creada correctamente.")

    payload = {
        "requested_flow": 9.0,
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal",
        "lot": user_lot[0].pk  # Lote con solicitud pendiente
    }
    print(f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"f❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    print("✅ No se pudo realizar la solicitud de cambio de caudal para un lote con solicitud pendiente.")

@pytest.mark.django_db
def test_user_cannot_request_higher_lot_flow_change_than_allowed(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    url = reverse("flow-request-create")
    payload = {
        "requeste_flow": 11.9,  # Caudal superior al permitido
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal",
        "lot": user_lot[0].pk
    }
    print(f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    print ("✅ No se pudo realizar la solicitud de cambio de caudal superior al permitido.")

@pytest.mark.django_db
def test_user_cannot_request_lot_flow_change_with_lacking_data_request(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    url = reverse("flow-request-create")
    payload = {
        "lot": user_lot[0].pk, # Falta el caudal solicitado
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal"
    }
    print (f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ se esperaba HTTP 400 pero se obtuvo {response.status_code}."
        f"Respuesta: {response.data}"
    )

    print ("✅ No se pudo realizar la solicitud de cambio de caudal sin caudal requerido.")

    payload = {
        "requested_flow": 10.5,  # Falta el lote
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal"
    }
    print (f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ se esperaba HTTP 400 pero se obtuvo {response.status_code}."
        f"Respuesta: {response.data}"
    )
    
    print ("✅ No se pudo realizar la solicitud de cambio de caudal sin lote requerido.")

    


@pytest.mark.django_db
def test_user_cannot_request_flow_change_for_lot_without_valve(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type):
    """
    ❌ Verifica que un usuario no pueda solicitar un cambio de caudal para un
    lote que no tiene válvula asociada.
    """
    
    # 🔐 Paso 3: Autenticación del usuario y obtención del token
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # 🔹 Paso 4: Construcción del payload
    url = reverse("flow-request-create")
    payload = {
        "requested_flow": 10.5,
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal",
        "lot": user_lot[1].pk  # Lote sin válvula asociada
    }
    print(f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    print ("✅ No se pudo realizar la solicitud de cambio de caudal para un lote sin válvula asociada.")

@pytest.mark.django_db
def test_user_cannot_request_flow_change_for_another_user_plot(api_client, normal_user, login_and_validate_otp, user_plot, user_lot, iot_device, device_type, crop_type, soil_type, person_type):
    """
    ❌ Verifica que un usuario no pueda solicitar un cambio de caudal para un
    dispositivo IoT asociado a otro predio.
    """
    NotProperUser = CustomUser.objects.create(
        document="0001112233344",
        password="UserPass123@",
        first_name="Not",
        last_name="Proper",
        email="",
        person_type=person_type,
        phone="123456789",
        is_registered=True,
    )
    NotProperPlot = Plot.objects.create(
        owner=NotProperUser,
        plot_name="predio2",
        is_activate=True,
        latitud=4,
        longitud=3,
        plot_extension=87
    )

    NotProperLot= Lot.objects.create(
        plot=NotProperPlot,
        crop_name="Maíz",
        crop_variety="Maíz 123",
        is_activate=True,
        crop_type=crop_type,
        soil_type=soil_type,
    )

    NotProperValveLot = IoTDevice.objects.create(
        device_type=device_type[6],
        name="Válvula de 4\"",
        iot_id=9,
        id_plot=NotProperPlot,
        id_lot=NotProperLot,
        is_active=True,
        actual_flow=4.0
    )
    

    
    # 🔐 Paso 3: Autenticación del usuario y obtención del token
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")

    # 🔹 Paso 4: Construcción del payload
    url = reverse("flow-request-create")
    payload = {
        "requested_flow": 10.5,
        "type": "Solicitud",
        "flow_request_type": "Cambio de Caudal",
        "lot": NotProperLot.pk  # Lote de otro usuario
    }
    print(f"Payload enviado: {payload}")
    response = client.post(url, payload, format="json")
    print(f"Respuesta ({response.status_code}): {response.data}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. "
        f"Respuesta: {response.data}"
    )
    print ("✅ No se pudo realizar la solicitud de cambio de caudal para otro predio.")

