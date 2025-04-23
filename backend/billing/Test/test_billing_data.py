import pytest
from django.urls import reverse
from rest_framework import status
from plots_lots.models import CropType
from billing.rates.models import TaxRate, FixedConsumptionRate, VolumetricConsumptionRate
from billing.company.models import Company

@pytest.mark.django_db
class TestRF51:
    """
    Pruebas para RF51: Validación de la actualización de tarifas y datos de empresa.
    
    Este conjunto de pruebas valida las historias de usuario relacionadas con la
    validación de cambios en las tarifas y datos de empresa en el módulo de facturación.
    """
    
    def test_hu01_access_billing_module(self, api_client, admin_user, login_and_validate_otp):
        """
        RF51-HU01: Visualización del acceso al módulo de "Facturación"
        
        Verifica que un usuario con rol autorizado pueda acceder al módulo de facturación
        y visualizar la información correspondiente.
        """
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Acceder al endpoint que devuelve la información de facturación
        url = reverse("rates-company")
        response = client.get(url)
        
        # Verificar acceso exitoso
        assert response.status_code == status.HTTP_200_OK, f"❌ Error al acceder al módulo de facturación: {response.data}"
        
        # Verificar que la respuesta contiene las secciones esperadas
        assert "company" in response.data, "❌ No se encontró la sección de datos de empresa"
        assert "tax_rates" in response.data, "❌ No se encontró la sección de tarifas de impuestos"
        assert "fixed_consumption_rates" in response.data, "❌ No se encontró la sección de tarifas fijas de consumo"
        assert "volumetric_consumption_rates" in response.data, "❌ No se encontró la sección de tarifas volumétricas de consumo"
        
        print("✅ RF51-HU01: Usuario autorizado puede acceder correctamente al módulo de facturación")

    def test_hu02_access_billing_management(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        RF51-HU02: Acceso al apartado de "Gestión de factura"
        
        Verifica que un usuario autorizado pueda acceder al apartado específico de gestión de facturas
        dentro del módulo de facturación.
        """
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Acceder al endpoint de gestión de facturación
        url = reverse("rates-company")
        response = client.get(url)
        
        # Verificar acceso exitoso
        assert response.status_code == status.HTTP_200_OK, f"❌ Error al acceder a la gestión de facturas: {response.data}"
        
        # Verificar que se puede acceder a los datos de la empresa
        assert "company" in response.data, "❌ No se pudo acceder a los datos de la empresa"
        
        print("✅ RF51-HU02: Usuario autorizado puede acceder correctamente a la gestión de facturas")

    def test_hu03_display_billing_form_data(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        RF51-HU03: Visualización del apartado de "Gestión de factura" e ingreso de datos
        
        Verifica que el sistema muestre correctamente todos los campos relacionados con
        la gestión de facturas y permita visualizar los datos actuales.
        """
        # Crear datos previos para las tarifas
        TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        maize = CropType.objects.create(name="Maíz")
        FixedConsumptionRate.objects.create(code="TFM", crop_type=maize, fixed_rate_cents=5000)
        VolumetricConsumptionRate.objects.create(code="TVM", crop_type=maize, volumetric_rate_cents=1000)
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Acceder al endpoint de gestión de facturación
        url = reverse("rates-company")
        response = client.get(url)
        
        # Verificar acceso exitoso y contenido completo
        assert response.status_code == status.HTTP_200_OK, f"❌ Error al obtener datos del formulario: {response.data}"
        
        # Verificar campos específicos en cada sección
        # 1. Datos de empresa
        assert "name" in response.data["company"], "❌ Falta el campo 'name' en datos de empresa"
        assert "nit" in response.data["company"], "❌ Falta el campo 'nit' en datos de empresa"
        
        # 2. Tarifas de impuestos
        assert len(response.data["tax_rates"]) > 0, "❌ No se encontraron tarifas de impuestos"
        assert "tax_type" in response.data["tax_rates"][0], "❌ Falta el campo 'tax_type' en tarifas de impuestos"
        assert "tax_value" in response.data["tax_rates"][0], "❌ Falta el campo 'tax_value' en tarifas de impuestos"
        
        # 3. Tarifas de consumo fijas
        assert len(response.data["fixed_consumption_rates"]) > 0, "❌ No se encontraron tarifas de consumo fijas"
        assert "crop_type" in response.data["fixed_consumption_rates"][0], "❌ Falta el campo 'crop_type' en tarifas de consumo fijas"
        
        # 4. Tarifas de consumo volumétricas
        assert len(response.data["volumetric_consumption_rates"]) > 0, "❌ No se encontraron tarifas de consumo volumétricas"
        assert "crop_type" in response.data["volumetric_consumption_rates"][0], "❌ Falta el campo 'crop_type' en tarifas de consumo volumétricas"
        
        print("✅ RF51-HU03: El sistema muestra correctamente todos los campos del formulario de gestión de facturas")

    def test_hu04_submit_changes(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        RF51-HU04: Envío de la información
        
        Verifica que el sistema permita enviar y procesar correctamente los cambios
        en la información de facturación.
        """
        # Crear datos previos para las tarifas
        tax = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        maize = CropType.objects.create(name="Maíz")
        fixed_rate = FixedConsumptionRate.objects.create(code="TFM", crop_type=maize, fixed_rate_cents=5000)
        volumetric_rate = VolumetricConsumptionRate.objects.create(code="TVM", crop_type=maize, volumetric_rate_cents=1000)
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Preparar datos para actualización
        payload = {
            "company": {
                "name": "AquaSmart Actualizado",
                "nit": "123456789"
            },
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 21.00
                }
            ],
            "fixed_consumption_rates": [
                {
                    "code": "TFM",
                    "crop_type": maize.id,
                    "fixed_rate_cents": 6000
                }
            ],
            "volumetric_consumption_rates": [
                {
                    "code": "TVM",
                    "crop_type": maize.id,
                    "volumetric_rate_cents": 1500
                }
            ]
        }
        
        # Enviar la actualización
        url = reverse("rates-company")
        response = client.patch(url, payload, format="json")
        
        # Verificar envío exitoso
        assert response.status_code == status.HTTP_200_OK, f"❌ Error al enviar cambios: {response.data}"
        
        # Verificar que los cambios se guardaron correctamente
        company = Company.objects.get(id_company=create_company.id_company)
        tax_refreshed = TaxRate.objects.get(id=tax.id)
        fixed_rate_refreshed = FixedConsumptionRate.objects.get(id=fixed_rate.id)
        volumetric_rate_refreshed = VolumetricConsumptionRate.objects.get(id=volumetric_rate.id)
        
        assert company.name == "AquaSmart Actualizado", f"❌ Nombre de empresa no actualizado: {company.name}"
        assert tax_refreshed.tax_value == 21.00, f"❌ Valor de impuesto no actualizado: {tax_refreshed.tax_value}"
        assert fixed_rate_refreshed.fixed_rate_cents == 6000, f"❌ Tarifa fija no actualizada: {fixed_rate_refreshed.fixed_rate_cents}"
        assert volumetric_rate_refreshed.volumetric_rate_cents == 1500, f"❌ Tarifa volumétrica no actualizada: {volumetric_rate_refreshed.volumetric_rate_cents}"
        
        print("✅ RF51-HU04: El sistema procesa correctamente los cambios enviados")

    def test_hu05_validate_no_changes(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        RF51-HU05: Validación de información repetida
        
        Verifica que el sistema valide correctamente cuando no hay cambios en la información
        y muestre el mensaje de error apropiado.
        """
        # Actualizar la empresa con datos específicos para esta prueba
        company = Company.objects.get(id_company=create_company.id_company)
        company.name = "AquaSmart Original"
        company.nit = "987654321"
        company.save()
        
        # Crear datos previos para las tarifas
        tax = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Preparar datos para actualización SIN CAMBIOS
        payload = {
            "company": {
                "name": "AquaSmart Original",
                "nit": "987654321"
            },
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 19.00
                }
            ]
        }
        
        # Enviar la actualización
        url = reverse("rates-company")
        response = client.patch(url, payload, format="json")
        
        # Verificar que se rechaza la actualización
        assert response.status_code == status.HTTP_400_BAD_REQUEST, f"❌ La actualización sin cambios fue aceptada incorrectamente: {response.data}"
        
        # Verificar el mensaje de error específico
        assert "error" in response.data, "❌ No se encontró mensaje de error en la respuesta"
        assert "Formulario sin cambios" in response.data["error"], f"❌ Mensaje de error incorrecto: {response.data['error']}"
        
        print("✅ RF51-HU05: El sistema valida correctamente cuando no hay cambios y muestra el mensaje apropiado")

    def test_hu05_validate_with_changes(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        RF51-HU05 (complementario): Validación cuando sí hay cambios
        
        Verifica que el sistema permita actualizar correctamente cuando al menos
        un campo tiene un valor diferente.
        """
        # Crear datos previos para las tarifas
        TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Configurar la empresa con un nombre válido para evitar errores de validación
        company = Company.objects.get(id_company=create_company.id_company)
        company.name = "AquaSmart Test"
        company.save()
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Preparar datos para actualización con UN SOLO CAMBIO
        payload = {
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 20.00  # Cambio de 19.00 a 20.00
                }
            ]
        }
        
        # Enviar la actualización
        url = reverse("rates-company")
        response = client.patch(url, payload, format="json")
        
        # Verificar actualización exitosa
        assert response.status_code == status.HTTP_200_OK, f"❌ Error al actualizar con un solo cambio: {response.data}"
        
        # Verificar que los cambios se guardaron correctamente
        updated_tax = TaxRate.objects.get(tax_type="IVA")
        assert updated_tax.tax_value == 20.00, f"❌ Valor de impuesto no actualizado: {updated_tax.tax_value}"
        
        print("✅ RF51-HU05 (complementario): El sistema permite actualizar cuando hay al menos un cambio")

    def test_unauthorized_access(self, api_client, regular_user, login_and_validate_otp):
        """
        Prueba complementaria: Acceso no autorizado
        
        Verifica que usuarios sin el rol adecuado no puedan acceder al módulo de facturación.
        """
        # Autenticar como usuario regular
        client = login_and_validate_otp(api_client, regular_user, "UserPass123@")
        
        # Intentar acceder al endpoint de gestión de facturación
        url = reverse("rates-company")
        response = client.get(url)
        
        # Verificar que se deniega el acceso
        assert response.status_code == status.HTTP_403_FORBIDDEN, f"❌ Usuario sin permisos pudo acceder al módulo: {response.status_code}"
        
        print("✅ Prueba complementaria: El sistema deniega correctamente el acceso a usuarios no autorizados")

    def test_partial_update_with_changes(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        Prueba complementaria: Actualización parcial
        
        Verifica que el sistema permita actualizar solo una sección (empresa, impuestos o consumo)
        sin necesidad de enviar todos los datos.
        """
        # Crear datos previos
        tax = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Preparar datos para actualización parcial (solo empresa)
        payload = {
            "company": {
                "name": "AquaSmart Parcial"
            }
        }
        
        # Enviar la actualización
        url = reverse("rates-company")
        response = client.patch(url, payload, format="json")
        
        # Verificar actualización exitosa
        assert response.status_code == status.HTTP_200_OK, f"❌ Error en actualización parcial: {response.data}"
        
        # Verificar que solo cambió el campo especificado
        company = Company.objects.get(id_company=create_company.id_company)
        assert company.name == "AquaSmart Parcial", f"❌ Nombre no actualizado: {company.name}"
        assert company.nit == create_company.nit, f"❌ NIT cambió inesperadamente: {company.nit}"
        
        print("✅ Prueba complementaria: El sistema permite actualizaciones parciales correctamente")

    def test_invalid_data_validation(self, api_client, admin_user, login_and_validate_otp, create_company):
        """
        Prueba complementaria: Validación de datos inválidos
        
        Verifica que el sistema valide correctamente los datos de entrada
        y rechace valores inválidos.
        """
        # Crear datos previos
        tax = TaxRate.objects.create(tax_type="IVA", tax_value=19.00)
        
        # Autenticar como administrador
        client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
        
        # Preparar datos inválidos (valor de impuesto fuera de rango)
        payload = {
            "tax_rates": [
                {
                    "tax_type": "IVA",
                    "tax_value": 101.00  # Inválido: mayor a 100%
                }
            ]
        }
        
        # Enviar la actualización
        url = reverse("rates-company")
        response = client.patch(url, payload, format="json")
        
        # Verificar que se rechaza la actualización
        assert response.status_code == status.HTTP_400_BAD_REQUEST, f"❌ Datos inválidos fueron aceptados: {response.data}"
        
        # Verificar que no cambió el valor en la base de datos
        tax_refreshed = TaxRate.objects.get(id=tax.id)
        assert tax_refreshed.tax_value == 19.00, f"❌ Valor de impuesto cambió a un valor inválido: {tax_refreshed.tax_value}"
        
        print("✅ Prueba complementaria: El sistema valida correctamente datos inválidos")