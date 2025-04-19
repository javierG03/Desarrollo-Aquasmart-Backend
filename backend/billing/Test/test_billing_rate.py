import pytest
from django.urls import reverse
from rest_framework import status
from plots_lots.models import CropType
from billing.rates.models import ConsumptionRate


@pytest.mark.django_db
def test_admin_can_add_consumption_rates(api_client, admin_user, login_and_validate_otp, create_company):
    """
    ✅ Verifica que un administrador pueda actualizar las tarifas de consumo
    """

    # 🔹 Crear tipos de cultivo y tarifas previas
    maize = CropType.objects.create(name="Maíz")
    rice = CropType.objects.create(name="Arroz")

    ConsumptionRate.objects.create(crop_type=maize, fixed_rate_cents=500, volumetric_rate_cents=1000)
    ConsumptionRate.objects.create(crop_type=rice, fixed_rate_cents=600, volumetric_rate_cents=1500)

    # 🔐 Login como admin
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")

    url = reverse("rates-company")
    print(f"URL generada: {url}")

    payload = {
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

    response = client.patch(url, payload, format="json")

    assert response.status_code == status.HTTP_200_OK, f"❌ Error al actualizar tarifas: {response.data}"
    print (f"Respuesta: {response.data}, Código de estado: {response.status_code}")
    # Validar cambios en la base de datos
    maize_rate = ConsumptionRate.objects.get(crop_type=maize)
    rice_rate = ConsumptionRate.objects.get(crop_type=rice)

    assert maize_rate.fixed_rate_cents == 700
    assert maize_rate.volumetric_rate_cents == 1200
    assert rice_rate.fixed_rate_cents == 800
    assert rice_rate.volumetric_rate_cents == 1800

    print("✅ Tarifas de consumo actualizadas correctamente.")

@pytest.mark.django_db
def test_update_consumption_rate_invalid_data_crop_type(api_client, admin_user, login_and_validate_otp, create_company):

    maize = CropType.objects.create(name="Maíz")

    ConsumptionRate.objects.create(crop_type=maize, fixed_rate_cents=500, volumetric_rate_cents=1000)
    
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse("rates-company")

    print(f"URL generada: {url}")

    payload = {
        "consumption_rates": [
            {"crop_type": maize.id,  # ID de cultivo existentes
             "fixed_rate_cents": "abcdef",
             "volumetric_rate_cents": 1200

             }
        ]
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"❌ El código de respuesta - {response.status_code} - no coincide con el esperado HTTP_400_BAD_REQUEST al ingresar los datos inválidos: {payload}. La respuesta de la aplicación es: {response.data}"
    print (f"Respuesta: {response.data}, Código de estado: {response.status_code}")
    maize_rate = ConsumptionRate.objects.get(crop_type=maize)
    assert maize_rate.fixed_rate_cents == 500, "❌ La tarifa de consumo se actualizó."
    assert maize_rate.volumetric_rate_cents == 1000
    print("✅ No se actualizó la tarifa con datos inválidos.")
    
    print(f"✅ tarifa de consumo:", maize_rate.fixed_rate_cents, maize_rate.volumetric_rate_cents)

@pytest.mark.django_db
def test_company_update_with_invalid_field(
    api_client, admin_user, login_and_validate_otp, create_company
):
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse("rates-company")

    payload = {
        "company": {

            "nit": 1234567890,  # NIT Válido
            "ciudad": 12345,  # Ciudad inválida
            "campo_invalido": "valor_invalido",  # Campo inválido
            "nombre": "AquaSmart 2" #Campo Inválido
        }
    }

    response = client.patch(url, payload, format="json")
    print (f"Respuesta: {response.data}, Código de estado: {response.status_code}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"❌ El código de respuesta - {response.status_code} - no coincide con el esperado HTTP_400_BAD_REQUEST al ingresar los datos inválidos: {payload}. La respuesta de la aplicación es: {response.data}"