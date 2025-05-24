import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from IA.models import ConsuptionPredictionLot, ClimateRecord
from users.models import CustomUser
from plots_lots.models import Lot, Plot
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


@pytest.mark.django_db
class TestRF78LotesDistritoPrediccion:
    """
    Test suite para RF78: Predicción de consumo de agua de cada lote del distrito
    """

    def setup_climate_data(self):
        """Crea datos climáticos necesarios para las predicciones"""
        ClimateRecord.objects.create(
            datetime=timezone.now() - timedelta(days=1),
            tempmax=30.5,
            tempmin=18.2,
            precip=5.2,
            precipprob=60.0,
            precipcover=40.0,
            windgust=15.5,
            windspeed=10.2,
            pressure=1013.25,
            cloudcover=45.0,
            solarradiation=850.0,
            sunrise="06:00:00",
            sunset="18:00:00",
            luminiscencia=12.0
        )

    # =====================================
    # TESTS DE PERMISOS Y ACCESO (HU01-HU03)
    # =====================================

    def test_HU01_admin_can_access_prediction_module(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU01: Rol autorizado puede acceder al módulo de predicciones para lotes del distrito
        """
        self.setup_climate_data()
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        response = client.get(url)
        
        # Admin debe poder acceder sin problemas
        assert response.status_code == status.HTTP_200_OK
        # Debe ver todas las predicciones existentes
        assert isinstance(response.data, list)

    def test_HU02_unauthorized_user_cannot_access(self, api_client, login_and_validate_otp, users, users_Lots, iot_device):
        """
        HU02: Usuario sin permisos no puede acceder al módulo
        """
        activeUser, _, _ = users
        
        # Remover todos los permisos de predicción del usuario
        activeUser.user_permissions.clear()
        
        client = login_and_validate_otp(api_client, activeUser)
        url = reverse('predicciones-lote')
        
        response = client.get(url)
        
        # Usuario sin permisos debe recibir error de permisos
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_HU03_user_with_limited_permissions_sees_only_own_lots(self, api_client, login_and_validate_otp, users, users_Lots, iot_device, admin_user):
        """
        HU03: Usuario con permisos limitados solo ve sus propios lotes
        """
        self.setup_climate_data()
        activeUser, _, _ = users
        ActiveUserActiveLot1, _, _ = users_Lots
        
        # Crear predicción del usuario normal
        client_user = login_and_validate_otp(api_client, activeUser)
        url = reverse('predicciones-lote')
        data = {"lot": ActiveUserActiveLot1.pk, "period_time": "1"}
        
        response_create = client_user.post(url, data, format="json")
        assert response_create.status_code == status.HTTP_201_CREATED

        # Crear predicción como admin para otro lote
        client_admin = login_and_validate_otp(api_client, admin_user)
        # Necesitamos crear un lote del admin para esta prueba
        admin_plot = Plot.objects.create(
            plot_name="Admin Plot",
            owner=admin_user,
            is_activate=True,
            latitud=2.2,
            longitud=3.3,
            plot_extension=10.0
        )
        
        # El usuario normal al listar solo debe ver sus propias predicciones
        response_user = client_user.get(url)
        assert response_user.status_code == status.HTTP_200_OK
        
        # Verificar que solo ve predicciones de sus lotes
        user_predictions = response_user.data
        for prediction in user_predictions:
            # El lote debe pertenecer al usuario
            lot = Lot.objects.get(pk=prediction['lot'])
            assert lot.plot.owner == activeUser

    def test_HU07_only_active_lots_can_create_predictions(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU07: Solo se pueden crear predicciones para lotes activos
        """
        self.setup_climate_data()
        _, _, ActiveUserInactiveLot = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        # Intentar crear predicción para lote inactivo
        data = {
            "lot": ActiveUserInactiveLot.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        
        # Debe fallar porque el lote está inactivo
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "lote" in str(response.data).lower() or "activ" in str(response.data).lower()

    def test_HU07_active_lots_can_create_predictions(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU07: Los lotes activos sí pueden crear predicciones
        """
        self.setup_clima_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        
        # Debe funcionar para lote activo
        assert response.status_code == status.HTTP_201_CREATED

    # =====================================
    # TESTS DE SELECCIÓN DE TIEMPO (HU19-HU20)
    # =====================================

    def test_HU19_valid_time_periods(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU19: Sistema acepta períodos de tiempo válidos (1, 3, 6 meses)
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        valid_periods = ["1", "3", "6"]
        
        for period in valid_periods:
            data = {
                "lot": ActiveUserActiveLot1.pk,
                "period_time": period
            }
            
            response = client.post(url, data, format="json")
            assert response.status_code == status.HTTP_201_CREATED, f"Período {period} debería ser válido"
            
            # Verificar que se crearon las predicciones correctas
            predictions = ConsuptionPredictionLot.objects.filter(
                lot=ActiveUserActiveLot1,
                period_time=period
            )
            assert predictions.count() == int(period), f"Deberían crearse {period} predicciones"

    def test_HU19_invalid_time_periods(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU19: Sistema rechaza períodos de tiempo inválidos
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        invalid_periods = ["0", "2", "4", "5", "7", "12", "abc", ""]
        
        for period in invalid_periods:
            data = {
                "lot": ActiveUserActiveLot1.pk,
                "period_time": period
            }
            
            response = client.post(url, data, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Período {period} debería ser inválido"

    # =====================================
    # TESTS DE VALIDACIÓN DE DATOS (HU22)
    # =====================================

    def test_HU22_error_when_no_climate_data(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU22: Error cuando no hay datos climáticos suficientes
        """
        # NO crear datos climáticos para esta prueba
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        
        # Debe fallar por falta de datos climáticos
        assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # El mensaje debe indicar problema con datos
        assert "datos" in str(response.data).lower() or "clima" in str(response.data).lower()

    # =====================================
    # TESTS DE PREDICCIONES EXISTENTES (Reutilización de datos - RF81)
    # =====================================

    def test_RF81_reuse_existing_predictions(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        RF81: Sistema reutiliza predicciones existentes dentro del período de validez
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "3"
        }
        
        # Primera predicción
        response1 = client.post(url, data, format="json")
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Intentar crear predicción duplicada inmediatamente
        response2 = client.post(url, data, format="json")
        
        # Debe fallar porque ya existe una predicción activa
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "existe" in str(response2.data).lower() or "activa" in str(response2.data).lower()

    def test_RF81_can_create_after_expiration(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        RF81: Puede crear nueva predicción después de que expire la anterior
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        # Crear predicción que ya esté vencida
        expired_prediction = ConsuptionPredictionLot.objects.create(
            user=admin_user,
            lot=ActiveUserActiveLot1,
            period_time="1",
            date_prediction=timezone.now().date(),
            consumption_prediction=100.0,
            code_prediction="EXPIRED001",
            final_date=timezone.now() - timedelta(days=1)  # Ya expiró
        )
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        
        # Debe permitir crear nueva predicción porque la anterior expiró
        assert response.status_code == status.HTTP_201_CREATED

    # =====================================
    # TESTS DE CONTENIDO DE PREDICCIONES (HU23)
    # =====================================

    def test_HU23_prediction_contains_required_data(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        HU23: La predicción contiene todos los datos requeridos
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "3"
        }
        
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar predicciones creadas en la base de datos
        predictions = ConsuptionPredictionLot.objects.filter(
            lot=ActiveUserActiveLot1,
            period_time="3"
        ).order_by('date_prediction')
        
        assert predictions.count() == 3, "Deben crearse 3 predicciones para 3 meses"
        
        for i, prediction in enumerate(predictions):
            # Verificar campos obligatorios
            assert prediction.user == admin_user
            assert prediction.lot == ActiveUserActiveLot1
            assert prediction.period_time == "3"
            assert prediction.consumption_prediction > 0, "Predicción debe ser positiva"
            assert prediction.code_prediction is not None
            assert prediction.final_date is not None
            assert prediction.date_prediction is not None
            
            # Verificar que las fechas de predicción son secuenciales por mes
            expected_month = (timezone.now().month + i) % 12
            if expected_month == 0:
                expected_month = 12
            assert prediction.date_prediction.month == expected_month or prediction.date_prediction.month == (expected_month + 1) % 12 or prediction.date_prediction.month == expected_month - 1

    def test_prediction_values_are_realistic(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        Verificar que los valores de predicción son realistas (positivos y en rango esperado)
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        prediction = ConsuptionPredictionLot.objects.filter(
            lot=ActiveUserActiveLot1,
            period_time="1"
        ).first()
        
        # Valores deben ser realistas para consumo de agua
        assert prediction.consumption_prediction > 0, "Consumo debe ser positivo"
        assert prediction.consumption_prediction < 1000000, "Consumo no debe ser excesivamente alto"

    # =====================================
    # TESTS DE DIFERENTES USUARIOS Y LOTES
    # =====================================

    def test_admin_can_predict_any_lot(self, api_client, login_and_validate_otp, admin_user, users, users_Lots, iot_device):
        """
        Admin puede crear predicciones para cualquier lote del distrito
        """
        self.setup_climate_data()
        activeUser, _, _ = users
        ActiveUserActiveLot1, _, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        # Admin crea predicción para lote de otro usuario
        data = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se creó correctamente
        prediction = ConsuptionPredictionLot.objects.filter(
            user=admin_user,  # Predicción creada por admin
            lot=ActiveUserActiveLot1  # Para lote de otro usuario
        ).first()
        
        assert prediction is not None
        assert prediction.lot.plot.owner == activeUser  # Lote pertenece al usuario normal
        assert prediction.user == admin_user  # Pero predicción fue creada por admin

    def test_user_cannot_predict_others_lots(self, api_client, login_and_validate_otp, admin_user, users, users_Lots, iot_device):
        """
        Usuario normal no puede crear predicciones para lotes de otros
        """
        self.setup_climate_data()
        activeUser, _, intrudeActiveUser = users
        ActiveUserActiveLot1, _, _ = users_Lots
        
        # El usuario "intruso" intenta crear predicción para lote que no es suyo
        client = login_and_validate_otp(api_client, intrudeActiveUser)
        url = reverse('predicciones-lote')
        
        data = {
            "lot": ActiveUserActiveLot1.pk,  # Lote que no le pertenece
            "period_time": "1"
        }
        
        response = client.post(url, data, format="json")
        
        # Debe fallar porque no es su lote
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # =====================================
    # TESTS DE INTEGRACIÓN COMPLETA
    # =====================================

    def test_complete_prediction_workflow(self, api_client, login_and_validate_otp, admin_user, users_Lots, iot_device):
        """
        Test de flujo completo: desde acceso hasta visualización de predicción
        """
        self.setup_climate_data()
        ActiveUserActiveLot1, ActiveUserActiveLot2, _ = users_Lots
        
        client = login_and_validate_otp(api_client, admin_user)
        url = reverse('predicciones-lote')
        
        # 1. Listar predicciones existentes (debe estar vacío)
        response_list = client.get(url)
        assert response_list.status_code == status.HTTP_200_OK
        assert len(response_list.data) == 0
        
        # 2. Crear predicción para primer lote
        data1 = {
            "lot": ActiveUserActiveLot1.pk,
            "period_time": "3"
        }
        response_create1 = client.post(url, data1, format="json")
        assert response_create1.status_code == status.HTTP_201_CREATED
        
        # 3. Crear predicción para segundo lote
        data2 = {
            "lot": ActiveUserActiveLot2.pk,
            "period_time": "1"
        }
        response_create2 = client.post(url, data2, format="json")
        assert response_create2.status_code == status.HTTP_201_CREATED
        
        # 4. Listar todas las predicciones
        response_list_final = client.get(url)
        assert response_list_final.status_code == status.HTTP_200_OK
        assert len(response_list_final.data) == 4  # 3 + 1 predicciones
        
        # 5. Verificar que las predicciones contienen información correcta
        all_predictions = ConsuptionPredictionLot.objects.all()
        assert all_predictions.count() == 4
        
        # Verificar códigos únicos
        codes = [p.code_prediction for p in all_predictions]
        assert len(set(codes)) == 2, "Debe haber 2 códigos únicos (uno por lote)"

    def setup_clima_data(self):
        """Alias para setup_climate_data para mantener consistencia"""
        self.setup_climate_data()