import pytest
from django.urls import reverse
from rest_framework import status
from plots_lots.models import CropType
from billing.rates.models import ConsumptionRate
from users.models import Otp


@pytest.mark.django_db
def test_admin_can_update_consumption_rates(api_client, admin_user, login_and_validate_otp):
    # 🔹 Crear tipos de cultivo
    maize = CropType.objects.create(name="Maíz")
    rice = CropType.objects.create(name="Arroz")

    # 🔹 Crear tarifas iniciales (valores en centavos)
    ConsumptionRate.objects.create(crop_type=maize, fixed_rate_cents=500, volumetric_rate_cents=1000)
    ConsumptionRate.objects.create(crop_type=rice, fixed_rate_cents=600, volumetric_rate_cents=1500)

    # 🔐 Autenticación
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")

    url = reverse("rates-company")

    # Nuevos datos para PATCH
    new_data = {
        "consumption_rates": [
            {
                "crop_type": maize.id,
                "fixed_rate_cents": 700,
                "volumetric_rate_cents": 1200
            },
            {
                "crop_type": rice.id,
                "fixed_rate_cents": 800,
                "volumetric_rate_cents": 1800
            }
        ]
    }

    response = client.patch(url, data=new_data, format="json")

    assert response.status_code == status.HTTP_200_OK

    # 🔎 Validaciones
    updated_maize = ConsumptionRate.objects.get(crop_type=maize)
    updated_rice = ConsumptionRate.objects.get(crop_type=rice)

    assert updated_maize.fixed_rate_cents == 700
    assert updated_maize.volumetric_rate_cents == 1200
    assert updated_rice.fixed_rate_cents == 800
    assert updated_rice.volumetric_rate_cents == 1800

    print("✅ Tarifas actualizadas correctamente por el administrador.")
