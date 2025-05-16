import pytest
from django.urls import reverse
from rest_framework import status
from communication.reports.models import TypeReport, FailureReport
from iot.models import DeviceType, IoTDevice
from plots_lots.models import Plot, Lot
from users.models import Otp

@pytest.mark.django_db
def test_application_failure_exists(api_client, normal_user, login_and_validate_otp):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse("app-failure-create")

    # Create a failure report
    response = client.post(
        url,
        {
            "observations": "Esto es una falla detallada del sistema",
            "type": "Reporte",
            "failure_type":"Fallo en el Aplicativo"
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["failure_type"] == TypeReport.APPLICATION_FAILURE

    url = reverse("app-failure-list")
    # Attempt to create the same failure report again
    response = client.get(
        url,
        {
         'id': response.data["id"],  
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_200_OK,(
        f"❌No se guardó el reporte de fallo en el aplicativo correctamente"
    )
    print ("✅El reporte de fallo se guardó correctamente")


@pytest.mark.django_db
def test_water_supply_failure_already_exists(api_client, normal_user, login_and_validate_otp, user_lot, user_plot, device_type, iot_device):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse("water-supply-failure-create")

    response = client.post(
        url,
        {
            "observations": "Esto es una falla detallada del sistema",
            "type": "Reporte",
            "failure_type":"Fallo en el Suministro del Agua",
            "lot": user_lot[0].pk
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["failure_type"] == TypeReport.WATER_SUPPLY_FAILURE
    url = reverse("water-supply-failure-list")

    response = client.get(
        url,
        {
         'id': response.data["id"],  
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_200_OK,(
        f"❌No se guardó el reporte de fallo en el suministro de agua correctamente"
    )

    url = reverse("water-supply-failure-create")
    # Se intenta crear el mismo reporte de fallo nuevamente
    response = client.post(
        url,
        {
            "observations": "Esto es una falla del sistema",
            "type": "Reporte",
            "failure_type":"Fallo en el Suministro del Agua",
            "lot": user_lot[0].pk
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST,(
        f"Se guardó el reporte de fallo en el suministro de agua al ya existir uno pendiente"
    )
    print("✅El reporte de fallo en un lote ya existente se rechzó correctamente")
    