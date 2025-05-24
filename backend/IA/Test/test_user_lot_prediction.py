import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from IA.models import ConsuptionPredictionLot, ClimateRecord
from users.models import CustomUser

@pytest.mark.django_db
def test_user_can_create_lot_consumption_prediction(api_client, login_and_validate_otp, users, users_Lots):
    """
    Verifica que un usuario pueda crear una predicción de consumo para su propio lote usando el endpoint y la API climática real.
    """
    activeUser, _, _ = users
    ActiveUserActiveLot1, _, _ = users_Lots

    # Autenticación del usuario
    client = login_and_validate_otp(api_client, activeUser, "UserPass123@")

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

    
    url = reverse('predicciones-lote')
    data = {
        "lot": ActiveUserActiveLot1.pk,
        "period_time": "3"
    }

    response = client.post(url, data, format="json")
    print("Request data:", data)
    print("Response status:", response.status_code)
    print("Response data:", response.data)

    # Depuración: Si falla, mostrar advertencia sobre datos climáticos
    if response.status_code != status.HTTP_201_CREATED:
        print("❌ Error al crear la predicción. Detalles:", response.data)
        print(
            "⚠️ Posible causa: ValueError: No se pudo obtener los datos necesarios para la predicción. "
            "Asegúrese que existan datos climáticos en la base de datos o que la API climática esté respondiendo correctamente."
        )
    assert response.status_code == status.HTTP_201_CREATED, response.data

    predictions = ConsuptionPredictionLot.objects.filter(
        user=activeUser,
        lot=ActiveUserActiveLot1,
        period_time="3"
    )
    print("Predictions found:", predictions.count())
    assert predictions.exists()
    for prediction in predictions:
        print(f"Prediction code: {prediction.code_prediction} |"
              f"fecha: {prediction.created_at.strftime('%Y-%m-%d %H:%M')}| "
              f"valor prediction: {prediction.consumption_prediction} L^3/s"
              )
        assert prediction.final_date is not None
        assert prediction.user == activeUser
        assert prediction.lot == ActiveUserActiveLot1
        assert prediction.code_prediction is not None