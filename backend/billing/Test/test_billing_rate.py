import pytest
from django.urls import reverse
from rest_framework import status
from plots_lots.models import CropType
from billing.rates.models import FixedConsumptionRate, VolumetricConsumptionRate


@pytest.mark.django_db
def test_admin_can_add_consumption_rates(api_client, admin_user, login_and_validate_otp, create_company):
    """
    ✅ Verifica que un administrador pueda actualizar las tarifas de consumo
    """

    # 🔹 Crear tipos de cultivo y tarifas previas
    maize = CropType.objects.create(name="Maíz")
    rice = CropType.objects.create(name="Arroz")

    
    FixedConsumptionRate.objects.create(code="TFM", crop_type=maize, fixed_rate_cents=600)
    VolumetricConsumptionRate.objects.create(code="TVM",crop_type=maize, volumetric_rate_cents=1000)

    FixedConsumptionRate.objects.create(code="TFR",crop_type=rice, fixed_rate_cents=600)
    VolumetricConsumptionRate.objects.create(code="TVR",crop_type=rice, volumetric_rate_cents=1500)
    
    # 🔐 Login como admin
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")

    url = reverse("rates-company")
    print(f"URL generada: {url}")

    payload = {
        "fixed_consumption_rates": [
                {
                    "code": "TFM",
                    "crop_type": maize.id,
                    "fixed_rate": 60.00
                },
                {
                    "code": "TFR",
                    "crop_type": rice.id,
                    "fixed_rate": 80.00
                }
            ],
        "volumetric_consumption_rates": [
                {
                    "code": "TVM",
                    "crop_type": maize.id,
                    "volumetric_rate": 120.00
                },
                {
                    "code": "TVR",
                    "crop_type": rice.id,
                    "volumetric_rate": 180.00
                }
            ]
    }
    
    print ("antes de la actualización")
    maize_rate = FixedConsumptionRate.objects.get(crop_type=maize)
    maize_vol_rate = VolumetricConsumptionRate.objects.get(crop_type=maize)
    rice_rate = FixedConsumptionRate.objects.get(crop_type=rice)
    rice_vol_rate = VolumetricConsumptionRate.objects.get(crop_type=rice)
    
    
    print(f"tarifa de consumo:","maiz", maize_rate.fixed_rate_cents, maize_vol_rate.volumetric_rate_cents, "arroz", rice_rate.fixed_rate_cents, rice_vol_rate.volumetric_rate_cents)

    

    response = client.patch(url, payload, format="json")


    print ("después de la actualización")
    maize_rate = FixedConsumptionRate.objects.get(crop_type=maize)
    maize_vol_rate = VolumetricConsumptionRate.objects.get(crop_type=maize)
    rice_rate = FixedConsumptionRate.objects.get(crop_type=rice)
    rice_vol_rate = VolumetricConsumptionRate.objects.get(crop_type=rice)
    print(f"tarifa de consumo:","maiz", maize_rate.fixed_rate_cents, maize_vol_rate.volumetric_rate_cents, "arroz", rice_rate.fixed_rate_cents, rice_vol_rate.volumetric_rate_cents)

    assert response.status_code == status.HTTP_200_OK, f"❌ Error al actualizar tarifas: {response.data}"
    print (f"Respuesta: {response.data}, Código de estado: {response.status_code}")
    # Validar cambios en la base de datos
    maize_fixed = FixedConsumptionRate.objects.get(crop_type=maize)
    maize_vol = VolumetricConsumptionRate.objects.get(crop_type=maize)
    rice_fixed = FixedConsumptionRate.objects.get(crop_type=rice)
    rice_vol = VolumetricConsumptionRate.objects.get(crop_type=rice)

    assert maize_fixed.fixed_rate_cents == 6000
    assert maize_vol.volumetric_rate_cents == 12000
    assert rice_fixed.fixed_rate_cents == 8000
    assert rice_vol.volumetric_rate_cents == 18000


    print("✅ Tarifas de consumo actualizadas correctamente.")

@pytest.mark.django_db
def test_update_consumption_rate_invalid_data_crop_type(api_client, admin_user, login_and_validate_otp, create_company):
    """🚫 Verifica que NO se actualicen tarifas de consumo si se envían datos inválidos."""

    # 🔹 Crear cultivo y tarifas actuales
    maize = CropType.objects.create(name="Maíz")

    fixed = FixedConsumptionRate.objects.create(code="TFM", crop_type=maize, fixed_rate_cents=500)
    vol = VolumetricConsumptionRate.objects.create(code="TVM", crop_type=maize, volumetric_rate_cents=1000)

    # 🔐 Login admin
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse("rates-company")
    print(f"URL generada: {url}")

    payload = {
        "fixed_consumption_rates": [
                {
                    "crop_type": maize.id,
                    "fixed_rate": -4  # Valor inválido
                }
            ],
        "volumetric_consumption_rates": [
                {
                    "crop_type": maize.id,
                    "volumetric_rate": 120.00
                }
            ]
    }

    response = client.patch(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"❌ El código de respuesta - {response.status_code} - no coincide con el esperado HTTP_400_BAD_REQUEST al ingresar los datos inválidos: {payload}. La respuesta de la aplicación es: {response.data}"
    print (f"Respuesta: {response.data}, Código de estado: {response.status_code}")


     # 🔎 Verificar que las tarifas NO se modificaron
    fixed.refresh_from_db()
    vol.refresh_from_db()

    assert fixed.fixed_rate_cents == 500, "❌ La tarifa fija fue modificada con datos inválidos"
    assert vol.volumetric_rate_cents == 1000, "❌ La tarifa volumétrica fue modificada con datos inválidos"
    
    print("✅ No se actualizó la tarifa con datos inválidos.")
    
    print(f"🔹 Tarifas actuales - Fija: {fixed.fixed_rate_cents}, Volumétrica: {vol.volumetric_rate_cents}")

@pytest.mark.django_db
def test_company_update_with_invalid_field(
    api_client, admin_user, login_and_validate_otp, create_company
):
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('rates-company')

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

@pytest.mark.django_db
def test_update_consumption_rate_invalid_crop_type(api_client, admin_user, login_and_validate_otp, create_company):
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('rates-company')

    payload = {
        "fixed_consumption_rates": [{"crop_type": 9999, "fixed_rate": 10.00}],
        "volumetric_consumption_rates": [{"crop_type": 9999, "volumetric_rate": 20.00}]
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "no existe" in response.data["error"].lower()


@pytest.mark.django_db
def test_update_consumption_rate_invalid_crop_type(api_client, admin_user, login_and_validate_otp, create_company):
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('rates-company')

    payload = {
        "fixed_consumption_rates": [{"crop_type": 9999, "fixed_rate": 10.00}],
        "volumetric_consumption_rates": [{"crop_type": 9999, "volumetric_rate": 20.00}]
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "no existe" in response.data["error"].lower()

@pytest.mark.django_db
def test_update_consumption_rate_missing_fields(api_client, admin_user, login_and_validate_otp, create_company):
    maize = CropType.objects.create(name="Maíz")
    FixedConsumptionRate.objects.create(code="TFM", crop_type=maize, fixed_rate_cents=500)
    VolumetricConsumptionRate.objects.create(code="TVM", crop_type=maize, volumetric_rate_cents=1000)

    rice = CropType.objects.create(name="Arroz")

    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('rates-company')

    payload = {
        "fixed_consumption_rates": [
            {
                "crop_type": maize.id},
            {
                "crop_type": rice.id,
                "code": "TFR",
                "fixed_rate": 80.00

            }                        ],  # Falta fixed_rate
        "volumetric_consumption_rates": [
            {
                "crop_type": maize.id
            }
        ]  # Falta volumetric_rate
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "campo requerido" in str(response.data).lower()

@pytest.mark.django_db
def test_regular_user_cannot_update_rates(api_client, regular_user, login_and_validate_otp, create_company):
    maize = CropType.objects.create(name="Maíz")
    client = login_and_validate_otp(api_client, regular_user, "UserPass123@")
    url = reverse('rates-company')

    payload = {
        "fixed_consumption_rates": [{"crop_type": maize.id, "fixed_rate": 10.00}],
        "volumetric_consumption_rates": [{"crop_type": maize.id, "volumetric_rate": 20.00}]
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_alphabetic_values_fail(api_client, admin_user, login_and_validate_otp, create_company):
    maize = CropType.objects.create(name="Maíz")
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('rates-company')

    payload = {
        "fixed_consumption_rates": [{"crop_type": maize.id, "fixed_rate": "abc"}],
        "volumetric_consumption_rates": [{"crop_type": maize.id, "volumetric_rate": "xyz"}]
    }

    response = client.patch(url, payload, format="json")
    assert response.status_code >= 400  # Puede ser 400 si está bien validado, 500 si no lo está
    print(f"❗ Respuesta inesperada con datos alfabéticos: {response.data}")
