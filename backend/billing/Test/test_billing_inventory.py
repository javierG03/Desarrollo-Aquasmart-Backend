import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from billing.bill.models import Bill
from billing.rates.models import FixedConsumptionRate, VolumetricConsumptionRate
from plots_lots.models import Plot, Lot, SoilType, CropType


@pytest.fixture
def soil_type(db):
    return SoilType.objects.create(name="Arcilloso")


@pytest.fixture
def crop_type(db):
    return CropType.objects.create(name="Maíz")


@pytest.fixture
def plot_user1(regular_user):
    return Plot.objects.create(
        plot_name="Predio Usuario 1",
        owner=regular_user,
        is_activate=True,
        latitud=1.1,
        longitud=2.2,
        plot_extension=5.0
    )


@pytest.fixture
def plot_admin(admin_user):
    return Plot.objects.create(
        plot_name="Predio Admin",
        owner=admin_user,
        is_activate=True,
        latitud=3.3,
        longitud=4.4,
        plot_extension=8.0
    )


@pytest.fixture
def lot_user1(plot_user1, crop_type, soil_type):
    return Lot.objects.create(
        plot=plot_user1,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Maíz Premium",
        crop_variety="Premium 100",
        is_activate=True
    )


@pytest.fixture
def lot_admin(plot_admin, crop_type, soil_type):
    return Lot.objects.create(
        plot=plot_admin,
        crop_type=crop_type,
        soil_type=soil_type,
        crop_name="Maíz Admin",
        crop_variety="Admin 200",
        is_activate=True
    )


@pytest.fixture
def consumption_rates(crop_type):
    fixed_rate = FixedConsumptionRate.objects.create(
        code="TFM",
        crop_type=crop_type,
        fixed_rate_cents=5000  # $50.00
    )
    volumetric_rate = VolumetricConsumptionRate.objects.create(
        code="TVM",
        crop_type=crop_type,
        volumetric_rate_cents=2000  # $20.00
    )
    return fixed_rate, volumetric_rate


@pytest.fixture
def complete_company(db):
    """Fixture que crea una empresa con todos los campos requeridos por Bill"""
    from billing.company.models import Company
    return Company.objects.create(
        name="AquaSmart Test Company",
        nit="123456789",
        address="Calle 123 # 45-67",
        phone="3001234567",
        email="empresa@test.com"
    )


@pytest.fixture
def bills_data(complete_company, regular_user, admin_user, lot_user1, lot_admin, consumption_rates):
    company = complete_company
    fixed_rate, volumetric_rate = consumption_rates
    
    # Crear facturas con diferentes estados y fechas
    bills = []
    
    # Crear facturas con campos ya poblados para evitar llamada a API
    # Factura pendiente - Usuario regular
    bill1 = Bill(
        company=company,
        client=regular_user,
        lot=lot_user1,
        fixed_consumption_rate=fixed_rate,
        volumetric_consumption_rate=volumetric_rate,
        fixed_rate_quantity=1,
        volumetric_rate_quantity=10,
        status='pendiente',
        # Campos que normalmente vienen de la API - pre-populados
        cufe='test-cufe-001',
        step_number='TEST001',
        qr_url='https://test-qr.com/001'
    )
    bill1.save()
    bills.append(bill1)
    
    # Factura pagada - Usuario regular
    bill2 = Bill(
        company=company,
        client=regular_user,
        lot=lot_user1,
        fixed_consumption_rate=fixed_rate,
        volumetric_consumption_rate=volumetric_rate,
        fixed_rate_quantity=1,
        volumetric_rate_quantity=15,
        status='pagada',
        cufe='test-cufe-002',
        step_number='TEST002',
        qr_url='https://test-qr.com/002'
    )
    bill2.save()
    bills.append(bill2)
    
    # Factura vencida - Admin
    bill3 = Bill(
        company=company,
        client=admin_user,
        lot=lot_admin,
        fixed_consumption_rate=fixed_rate,
        volumetric_consumption_rate=volumetric_rate,
        fixed_rate_quantity=1,
        volumetric_rate_quantity=8,
        status='vencida',
        cufe='test-cufe-003',
        step_number='TEST003',
        qr_url='https://test-qr.com/003'
    )
    bill3.save()
    bills.append(bill3)
    
    # Factura validada - Admin
    bill4 = Bill(
        company=company,
        client=admin_user,
        lot=lot_admin,
        fixed_consumption_rate=fixed_rate,
        volumetric_consumption_rate=volumetric_rate,
        fixed_rate_quantity=1,
        volumetric_rate_quantity=12,
        status='validada',
        cufe='test-cufe-004',
        step_number='TEST004',
        qr_url='https://test-qr.com/004'
    )
    bill4.save()
    bills.append(bill4)
    
    return bills


class TestRF83BillReports:
    """
    Test suite para RF83: Informe y totalización de facturas
    """
    
    def test_rf83_hu01_visualizar_facturas_filtradas(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU01: Visualización de informe de facturas filtradas
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        # Filtrar solo facturas pendientes
        url = reverse('bill-totalization')
        response = client.get(url, {'status': ['pendiente']})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Verificar que solo hay facturas pendientes
        assert len(data) == 1
        assert data[0]['status'] == 'pendiente'
        assert data[0]['cantidad_facturas'] == 1
        
    def test_rf83_hu01_filtros_multiples(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU01: Filtros múltiples funcionando correctamente
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        # Filtrar por múltiples estados
        url = reverse('bill-totalization')
        response = client.get(url, {'status': ['pendiente', 'pagada']})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Verificar que hay 2 estados diferentes
        estados = [item['status'] for item in data]
        assert 'pendiente' in estados
        assert 'pagada' in estados
        assert len(data) == 2
        
    def test_rf83_hu03_totalizacion_por_estado(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU03: Selección del botón "Totalizar" - Mostrar resumen por estado
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        url = reverse('bill-totalization')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Verificar estructura de totalización
        for item in data:
            assert 'status' in item
            assert 'cantidad_facturas' in item
            assert 'cantidad_usuarios' in item
            assert 'cantidad_predios' in item
            assert 'cantidad_lotes' in item
            assert 'monto_total' in item
            
        # Verificar que tenemos todos los estados
        estados = [item['status'] for item in data]
        assert len(estados) == 4  # pendiente, pagada, vencida, validada
        
            
    def test_rf83_hu06_descarga_pdf(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU06: Selección del botón "Descargar" - PDF
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        url = reverse('export-bills-pdf')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        assert 'attachment' in response['Content-Disposition']
        assert 'informe_facturas_' in response['Content-Disposition']
        
    def test_rf83_hu06_descarga_excel(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU06: Selección del botón "Descargar" - Excel
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        url = reverse('export-bills-excel')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response['Content-Disposition']
        assert 'informe_facturas_' in response['Content-Disposition']
        
    def test_rf83_hu06_descarga_con_filtros(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83-HU06: Descarga respeta los filtros aplicados
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        # Descargar PDF solo con facturas pagadas
        url = reverse('export-bills-pdf')
        response = client.get(url, {'status': ['pagada']})
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        
        # Descargar Excel solo con facturas pagadas
        url = reverse('export-bills-excel')
        response = client.get(url, {'status': ['pagada']})
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
    def test_rf83_filtro_rango_fechas(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        Verificar filtrado por rango de fechas
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        # Filtrar por fecha de hoy
        today = timezone.now().date()
        url = reverse('bill-totalization')
        response = client.get(url, {
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d')
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        
        # Todas las facturas fueron creadas hoy
        total_facturas = sum(item['cantidad_facturas'] for item in data)
        assert total_facturas == 4
        
    def test_rf83_sin_facturas_filtradas(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        Verificar comportamiento cuando no hay facturas que coincidan con el filtro
        """
        client = login_and_validate_otp(api_client, admin_user)
        
        # Filtrar por un estado que no existe
        url = reverse('bill-totalization')
        response = client.get(url, {'status': ['inexistente']})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) == 0
        
   
        
    def test_rf83_performance_descarga_tiempo(self, api_client, login_and_validate_otp, admin_user, bills_data):
        """
        RF83: Verificar que la descarga se realiza en menos de 4 segundos (criterio de aceptación)
        """
        import time
        client = login_and_validate_otp(api_client, admin_user)
        
        # Test PDF
        start_time = time.time()
        url = reverse('export-bills-pdf')
        response = client.get(url)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < 4.0  # Menos de 4 segundos
        
        # Test Excel
        start_time = time.time()
        url = reverse('export-bills-excel')
        response = client.get(url)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < 4.0  # Menos de 4 segundos