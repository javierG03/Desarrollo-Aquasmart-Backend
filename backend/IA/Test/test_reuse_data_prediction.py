import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from IA.models import ClimateRecord, ConsuptionPredictionLot

@pytest.mark.django_db
def test_reuse_climate_data_for_prediction(api_client, login_and_validate_otp, users, users_Lots):
    """
    Verifica que si ya existen datos climáticos válidos, NO se realiza un nuevo llamado a la API externa
    y se reutilizan los datos almacenados para la predicción.
    """
    activeUser, _, _ = users
    ActiveUserActiveLot1, _, _ = users_Lots

    # Autenticación del usuario
    client = login_and_validate_otp(api_client, activeUser, "UserPass123@")

    # 1. Primer llamado: obtener y almacenar datos climáticos reales
    url = reverse('fetch-climate-data')
    data = {
        'location': '4.60971%2C-74.08175',  # Bogotá, Colombia
        'date': timezone.now().strftime("%Y-%m-%d")
    }
    response = client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED or response.status_code == status.HTTP_200_OK
    assert 'message' in response.data

    # Guardar el ID del registro climático más reciente
    climate_record = ClimateRecord.objects.latest('datetime')
    climate_record_id = climate_record.id

    # 2. Segundo llamado: debe reutilizar el registro existente (no llamar a la API)
    response2 = client.post(url, data, format='json')
    assert response2.status_code == status.HTTP_200_OK
    assert 'Ya existe un registro con datos válidos.' in response2.data['message']
    assert 'record' in response2.data

    # Verificar que el registro climático es el mismo (no se creó uno nuevo)
    latest_climate_record = ClimateRecord.objects.latest('datetime')
    assert latest_climate_record.id == climate_record_id

    # 3. Realizar predicción usando los datos almacenados
    url_pred = reverse('predicciones-lote')
    data_pred = {
        "lot": ActiveUserActiveLot1.pk,
        "period_time": "3"
    }
    response_pred = client.post(url_pred, data_pred, format="json")
    print("Request data:", data_pred)
    print("Response status:", response_pred.status_code)
    print("Response data:", response_pred.data)

    assert response_pred.status_code == status.HTTP_201_CREATED, response_pred.data

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