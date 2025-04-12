import pytest
from django.urls import reverse
from rest_framework import status
from plots_lots.models import CropType
from billing.rates.models import TaxRate, ConsumptionRate
from billing.company.models import Company

@pytest.mark.django_db
class TestBillingRateUpdate:
    """Pruebas para validar el RF51: Validación de actualización de tarifas y datos"""
    
    def test_unauthorized_user_cannot_access_rates(self, api_client, create_company):
        """Verifica que usuarios no autenticados no puedan acceder a las tarifas (HU01)"""
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
    def test_regular_user_cannot_update_rates(self, api_client, regular_user, login_and_validate_otp, create_company):
        """Verifica que usuarios normales no puedan actualizar tarifas (HU02)"""
        # Configurar cliente y autenticar como usuario normal
        client = login_and_validate_otp(api_client, regular_user, "UserPass123@")
        
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        
        # Intentar actualizar datos
        response = client.patch(url, {"company": {"nombre": "Nueva Empresa"}}, format="json")
        
        # Debería recibir acceso denegado
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_admin_can_view_rates_and_company_data(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que el administrador pueda ver los datos de tarifas y empresa (HU03)"""
        # Crear datos iniciales
        tax_rate = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        crop_type = CropType.objects.create(name="Maíz")
        consumption_rate = ConsumptionRate.objects.create(
            crop_type=crop_type, 
            fixed_rate_cents=5000, 
            volumetric_rate_cents=2500
        )
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Solicitar datos
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        response = client.get(url)
        
        # Verificar respuesta
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estructura de datos
        assert "company" in response.data
        assert "tax_rates" in response.data
        assert "consumption_rates" in response.data
        
        # Verificar contenido
        assert response.data["company"]["nombre"] == "AquaSmart"
        assert response.data["company"]["nit"] == "123456789"
        assert response.data["tax_rates"][0]["tax_type"] == "IVA"
        assert float(response.data["tax_rates"][0]["tax_value"]) == 19.00
        assert response.data["consumption_rates"][0]["crop_type"] == crop_type.id
        assert float(response.data["consumption_rates"][0]["fixed_rate"]) == 50.00  # 5000 centavos = 50 pesos
    
    def test_update_with_no_changes_fails(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que enviar actualización sin cambios genere error (HU05)"""
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Enviar los mismos datos existentes
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "company": {
                "nombre": "AquaSmart",
                "nit": "123456789",
                "ciudad": "Bogotá"
            }
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar rechazo con mensaje correcto
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Formulario sin cambios" in response.data["error"]
    
    def test_update_company_data_success(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que se puedan actualizar datos de la empresa (HU04, HU05)"""
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Actualizar solo la ciudad
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "company": {
                "ciudad": "Medellín"  # Cambio de ciudad
            }
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar éxito
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar cambio en BD
        company = Company.objects.first()
        assert company.ciudad == "Medellín"
        assert company.nombre == "AquaSmart"  # No cambió
    
    def test_update_tax_rates_success(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que se puedan actualizar tarifas de impuestos (HU04, HU05)"""
        # Crear datos iniciales
        tax_rate = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Actualizar valor del impuesto
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 16.00  # Cambio de tarifa
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar éxito
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar cambio en BD
        tax_rate.refresh_from_db()
        assert float(tax_rate.tax_value) == 16.00
    
    def test_update_consumption_rates_success(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que se puedan actualizar tarifas de consumo (HU04, HU05)"""
        # Crear datos iniciales
        crop_type = CropType.objects.create(name="Maíz")
        consumption_rate = ConsumptionRate.objects.create(
            crop_type=crop_type, 
            fixed_rate_cents=5000, 
            volumetric_rate_cents=2500
        )
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Actualizar tarifas de consumo
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "consumption_rates": [
                {
                    "crop_type": crop_type.id,
                    "fixed_rate": 60.00,  # 6000 centavos
                    "volumetric_rate": 30.00  # 3000 centavos
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar éxito
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar cambio en BD
        consumption_rate.refresh_from_db()
        assert consumption_rate.fixed_rate_cents == 6000
        assert consumption_rate.volumetric_rate_cents == 3000
    
    def test_update_multiple_entities(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que se puedan actualizar múltiples entidades en una sola operación (HU04, HU05)"""
        # Crear datos iniciales
        tax_rate = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        crop_type = CropType.objects.create(name="Maíz")
        consumption_rate = ConsumptionRate.objects.create(
            crop_type=crop_type, 
            fixed_rate_cents=5000, 
            volumetric_rate_cents=2500
        )
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Actualizar múltiples entidades
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "company": {
                "nombre": "AquaSmart Renovado"
            },
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 16.00
                }
            ],
            "consumption_rates": [
                {
                    "crop_type": crop_type.id,
                    "fixed_rate": 60.00  # 6000 centavos
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar éxito
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar cambios en BD
        company = Company.objects.first()
        tax_rate.refresh_from_db()
        consumption_rate.refresh_from_db()
        
        assert company.nombre == "AquaSmart Renovado"
        assert float(tax_rate.tax_value) == 16.00
        assert consumption_rate.fixed_rate_cents == 6000
        assert consumption_rate.volumetric_rate_cents == 2500  # No cambió
    
    def test_update_with_invalid_tax_value(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica el rechazo de valores de impuesto fuera de rango"""
        # Crear datos iniciales
        tax_rate = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Intentar actualizar con valor inválido
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 101.00  # Valor fuera de rango (debería ser 0-100)
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar rechazo
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_nonexistent_tax_type(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica el manejo de errores al actualizar un tipo de impuesto que no existe"""
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Intentar actualizar tipo inexistente
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "tax_rates": [
                {
                    "tax_type": "IMPUESTO_INEXISTENTE",
                    "tax_value": 15.00
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar rechazo con mensaje apropiado
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no existe" in response.data["error"]
    
    def test_transaction_rollback_on_error(self, api_client, admin_user, login_and_validate_otp, create_company):
        """Verifica que se haga rollback de todas las actualizaciones si alguna falla"""
        # Crear datos iniciales
        tax_rate = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Enviar actualización con parte válida y parte inválida
        url = reverse("rates-company")
        print(f"URL generada: {url}")
        payload = {
            "company": {
                "nombre": "Nuevo Nombre"  # Válido
            },
            "tax_rates": [
                {
                    "tax_type": "INEXISTENTE",  # Inválido - no existe
                    "tax_value": 10.00
                }
            ]
        }
        
        response = client.patch(url, payload, format="json")
        
        # Verificar rechazo
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]
        
        # Verificar que ningún cambio se haya guardado
        company = Company.objects.first()
        assert company.nombre == "AquaSmart"  # No debe haber cambiado