import pytest
from django.urls import reverse
from rest_framework import status
from communication.reports.models import TypeReport, FailureReport
from iot.models import DeviceType, IoTDevice
from plots_lots.models import Plot, Lot
from users.models import Otp


@pytest.mark.django_db
def test_application_failure_requires_valid_observations(api_client, normal_user, login_and_validate_otp):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse("app-failure-create")

    # Observaciones muy cortas
    response = client.post(url, {"observations": "corto", "type": "Reporte", "failure_type":"Fallo en el Aplicativo"}, format="json")
    print(f"Response: {response.data}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. Se esperaba un error de validación para observaciones muy cortas."
    )
    assert "observaciones" in response.data

    # Observaciones válidas
    response2 = client.post(url, {"observations": "Esto es una falla detallada del sistema", "type": "Reporte", "failure_type":"Fallo en el Aplicativo"}, format="json")
    assert response2.status_code == status.HTTP_201_CREATED
    assert response2.data["failure_type"] == TypeReport.APPLICATION_FAILURE

    print("✅ Reporte de fallo en aplicativo validado correctamente.")

@pytest.mark.django_db
def test_application_failure_cannot_has_more_than_200_characteres(
    api_client, normal_user, login_and_validate_otp
):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse("app-failure-create")

    response = client.post(
        url,
        {
            "observations": "a" * 201,
            "type": "Reporte",
            "failure_type":"Fallo en el Aplicativo"
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"❌ Se esperaba HTTP 400 pero se obtuvo {response.status_code}. Se esperaba un error de validación para observaciones muy largas."
    )
    print(f"Response: {response.data}, status_code: {response.status_code}")

    print("✅ Reporte de fallo en aplicativo validado correctamente.")



