import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from IA.models import ClimateRecord
from users.models import CustomUser


@pytest.mark.django_db
class TestRF77ClimateDataObtention:
    """
    Tests para RF77: Obtención de datos ambientales para el modelo de predicción
    HU01: Obtención de datos ambientales (10 puntos)
    
    Criterios de aceptación:
    - El sistema debe obtener datos de la API con todas las variables requeridas
    - Los datos deben almacenarse en la base de datos para su uso en el modelo predictivo
    - La consulta a la API meteorológica no debe demorar más de 5 segundos
    """

    def test_fetch_climate_data_endpoint_with_real_api(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica que el endpoint fetch-climate-data funcione con la API real
        y obtenga todos los datos requeridos según los criterios de aceptación
        """
        # Autenticar como admin
        client = login_and_validate_otp(api_client, admin_user)
        
        # URL real del sistema según IA/urls.py
        url = reverse('fetch-climate-data')
        
        # Datos de solicitud con ubicación de Bogotá y fecha actual
        data = {
            'location': '4.60971%2C-74.08175',  # Bogotá, Colombia
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        # Realizar solicitud POST
        response = client.post(url, data, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        assert 'message' in response.data
        assert 'records' in response.data
        
        # Verificar que se creó el registro en la base de datos
        climate_record = ClimateRecord.objects.latest('datetime')
        assert climate_record is not None
        
        # Verificar todos los campos requeridos por RF77
        required_fields = [
            'datetime', 'tempmax', 'tempmin', 'precip', 'precipprob',
            'precipcover', 'windgust', 'windspeed', 'pressure', 
            'cloudcover', 'solarradiation', 'sunrise', 'sunset',
            'luminiscencia', 'final_date'
        ]
        
        for field in required_fields:
            assert hasattr(climate_record, field)
            field_value = getattr(climate_record, field)
            assert field_value is not None, f"Campo {field} no debe ser nulo"
        
        # Verificar cálculo automático de luminiscencia
        assert climate_record.luminiscencia > 0
        
        # Verificar cálculo automático de final_date (7 días después)
        expected_final_date = climate_record.datetime + timedelta(days=7)
        assert climate_record.final_date.date() == expected_final_date.date()

    def test_climate_data_cache_system(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica el sistema de caché para evitar solicitudes innecesarias a la API
        Reutilización de datos según RF81
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('fetch-climate-data')
        
        # Crear registro climático vigente (menos de 7 días)
        existing_record = ClimateRecord.objects.create(
            datetime=timezone.now() - timedelta(days=3),
            tempmax=25.5,
            tempmin=15.2,
            precip=0.0,
            precipprob=20.0,
            precipcover=10.0,
            windgust=15.0,
            windspeed=10.0,
            pressure=1013.25,
            cloudcover=30.0,
            solarradiation=500.0,
            sunrise=datetime.strptime("06:00:00", "%H:%M:%S").time(),
            sunset=datetime.strptime("18:00:00", "%H:%M:%S").time(),
            luminiscencia=12.0,
            final_date=timezone.now() + timedelta(days=4)  # Aún vigente
        )
        
        data = {
            'location': '4.60971%2C-74.08175',
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        # Primera solicitud debe usar datos en caché
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Ya existe un registro con datos válidos' in response.data['message']
        assert 'record' in response.data
        
        # Verificar que el registro devuelto es el existente
        returned_record = response.data['record']
        assert returned_record['tempmax'] == 25.5
        assert returned_record['tempmin'] == 15.2

    def test_climate_data_expiration(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica que los datos expirados se renueven automáticamente
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('fetch-climate-data')
        
        # Crear registro climático expirado (más de 7 días)
        expired_record = ClimateRecord.objects.create(
            datetime=timezone.now() - timedelta(days=10),
            tempmax=20.0,
            tempmin=10.0,
            precip=5.0,
            precipprob=80.0,
            precipcover=60.0,
            windgust=20.0,
            windspeed=15.0,
            pressure=1010.0,
            cloudcover=70.0,
            solarradiation=300.0,
            sunrise=datetime.strptime("06:30:00", "%H:%M:%S").time(),
            sunset=datetime.strptime("17:30:00", "%H:%M:%S").time(),
            luminiscencia=11.0,
            final_date=timezone.now() - timedelta(days=3)  # Expirado
        )
        
        data = {
            'location': '4.60971%2C-74.08175',
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        # Solicitud debe obtener nuevos datos de la API
        response = client.post(url, data, format='json')
        
        # Debe crear nuevos datos, no usar caché
        assert response.status_code == status.HTTP_201_CREATED
        assert 'obtenidos y guardados con éxito' in response.data['message']
        
        # Verificar que hay un nuevo registro más reciente
        latest_record = ClimateRecord.objects.latest('datetime')
        assert latest_record.pk != expired_record.pk
        assert latest_record.datetime > expired_record.datetime

    def test_latest_climate_data_endpoint(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica el endpoint para obtener el último registro climático
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('latest-climate')
        
        # Crear registro climático
        climate_record = ClimateRecord.objects.create(
            datetime=timezone.now(),
            tempmax=28.0,
            tempmin=18.0,
            precip=2.5,
            precipprob=40.0,
            precipcover=25.0,
            windgust=12.0,
            windspeed=8.0,
            pressure=1015.0,
            cloudcover=45.0,
            solarradiation=600.0,
            sunrise=datetime.strptime("05:45:00", "%H:%M:%S").time(),
            sunset=datetime.strptime("18:15:00", "%H:%M:%S").time(),
            luminiscencia=12.5,
            final_date=timezone.now() + timedelta(days=7)
        )
        
        # Solicitar último registro
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar datos del registro más reciente
        data = response.data
        assert data['tempmax'] == 28.0
        assert data['tempmin'] == 18.0
        assert data['precip'] == 2.5
        assert data['luminiscencia'] == 12.5

    def test_latest_climate_data_empty_database(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica manejo cuando no hay registros climáticos
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('latest-climate')
        
        # Asegurar que no hay registros
        ClimateRecord.objects.all().delete()
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No hay registros climáticos disponibles' in response.data['message']

    def test_climate_data_validation_automatic_fields(self):
        """
        Test HU01: Verifica que los campos automáticos se calculen correctamente
        (luminiscencia y final_date)
        """
        # Crear registro con solo campos básicos
        climate_record = ClimateRecord(
            datetime=timezone.now(),
            tempmax=25.0,
            tempmin=15.0,
            precip=0.0,
            precipprob=20.0,
            precipcover=10.0,
            windgust=15.0,
            windspeed=10.0,
            pressure=1013.0,
            cloudcover=30.0,
            solarradiation=500.0,
            sunrise=datetime.strptime("06:00:00", "%H:%M:%S").time(),
            sunset=datetime.strptime("18:00:00", "%H:%M:%S").time()
            # luminiscencia y final_date deben calcularse automáticamente
        )
        
        # Guardar debe calcular campos automáticos
        climate_record.save()
        
        # Verificar cálculo de luminiscencia
        assert climate_record.luminiscencia is not None
        assert climate_record.luminiscencia == 12.0  # 18:00 - 06:00 = 12 horas
        
        # Verificar cálculo de final_date (7 días después)
        expected_final_date = climate_record.datetime + timedelta(days=7)
        assert climate_record.final_date.date() == expected_final_date.date()

    def test_climate_data_api_timeout_compliance(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica que la consulta a la API no demore más de 5 segundos
        """
        import time
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('fetch-climate-data')
        
        data = {
            'location': '4.60971%2C-74.08175',
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        # Medir tiempo de respuesta
        start_time = time.time()
        response = client.post(url, data, format='json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Verificar que no demora más de 5 segundos (criterio de aceptación)
        assert response_time <= 5.0, f"La API demoró {response_time:.2f} segundos, debe ser ≤ 5 segundos"
        
        # Verificar respuesta exitosa
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_climate_data_all_required_fields_from_api(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica que se obtengan todos los campos requeridos especificados en RF77
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('fetch-climate-data')
        
        data = {
            'location': '4.60971%2C-74.08175',
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        response = client.post(url, data, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        
        # Obtener último registro creado
        latest_record = ClimateRecord.objects.latest('datetime')
        
        # Verificar todos los campos especificados en RF77
        rf77_required_fields = {
            'Año': latest_record.datetime.year,
            'Mes_numero': latest_record.datetime.month,
            'Temperatura Minima(°C)': latest_record.tempmin,
            'Temperatura Maxima(°C)': latest_record.tempmax,
            'Precipitacion(mm)': latest_record.precip,
            'Probabilidad de Precipitacion(%)': latest_record.precipprob,
            'Cubrimiento de Precipitacion(%)': latest_record.precipcover,
            'Presión del nivel del Mar (mbar)': latest_record.pressure,
            'Nubosidad (%)': latest_record.cloudcover,
            'Radiación Solar (W/m2)': latest_record.solarradiation,
            'Velocidad del Viento (km/h)': latest_record.windspeed,
            'Salida del Sol': latest_record.sunrise,
            'Puesta del Sol': latest_record.sunset,
            'Luminiscencia': latest_record.luminiscencia
        }
        
        # Verificar que todos los campos tienen valores válidos
        for field_name, field_value in rf77_required_fields.items():
            assert field_value is not None, f"Campo {field_name} no debe ser nulo"
            if isinstance(field_value, (int, float)):
                assert field_value >= 0 or field_name in ['Temperatura Minima(°C)'], f"Campo {field_name} debe tener valor válido"

    def test_climate_data_storage_persistence(self, api_client, admin_user, login_and_validate_otp):
        """
        Test HU01: Verifica que los datos se almacenen correctamente en la base de datos
        para su uso en el modelo predictivo
        """
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('fetch-climate-data')
        
        # Contar registros antes
        initial_count = ClimateRecord.objects.count()
        
        data = {
            'location': '4.60971%2C-74.08175',
            'date': timezone.now().strftime("%Y-%m-%d")
        }
        
        response = client.post(url, data, format='json')
        
        # Verificar que se creó nuevo registro si no había caché
        if response.status_code == status.HTTP_201_CREATED:
            final_count = ClimateRecord.objects.count()
            assert final_count > initial_count, "Debe crear nuevo registro en la base de datos"
            
            # Verificar que el registro se puede recuperar para el modelo predictivo
            latest_record = ClimateRecord.objects.latest('datetime')
            assert latest_record.datetime is not None
            assert latest_record.final_date > timezone.now()  # Vigente para uso futuro
            
            # Verificar estructura de datos compatible con modelo IA
            model_data = {
                'Año': str(latest_record.datetime.year),
                'Mes_numero': str(latest_record.datetime.month),
                'Temperatura Minima(°C)': latest_record.tempmin,
                'Temperatura Maxima(°C)': latest_record.tempmax,
                'Precipitacion(mm)': latest_record.precip,
                'Probabilidad de Precipitacion(%)': latest_record.precipprob,
                'Cubrimiento de Precipitacion(%)': latest_record.precipcover,
                'Presión del nivel del Mar (mbar)': latest_record.pressure,
                'Nubosidad (%)': latest_record.cloudcover,
                'Radiación Solar (W/m2)': latest_record.solarradiation,
                'Velocidad del Viento (km/h)': latest_record.windspeed,
                'Luminiscencia': latest_record.luminiscencia
            }
            
            # Verificar que todos los campos necesarios para el modelo están presentes
            for key, value in model_data.items():
                assert value is not None, f"Campo {key} requerido para modelo IA no debe ser nulo"