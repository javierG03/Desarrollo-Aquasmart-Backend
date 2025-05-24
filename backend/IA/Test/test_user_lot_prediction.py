import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from IA.models import ConsuptionPredictionLot
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
    url = reverse('predicciones-lote')
    data = {
        "lot": ActiveUserActiveLot1.pk,
        "period_time": "3"
    }

    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data

    predictions = ConsuptionPredictionLot.objects.filter(
        user=activeUser,
        lot=ActiveUserActiveLot1,
        period_time="3"
    )
    assert predictions.exists()
    for prediction in predictions:
        assert prediction.final_date is not None
        assert prediction.user == activeUser
        assert prediction.lot == ActiveUserActiveLot1
        assert prediction.code_prediction is not None