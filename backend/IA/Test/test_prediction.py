import pytest
from django.utils import timezone
from IA.models import ConsuptionPredictionLot


@pytest.mark.django_db
def test_create_consumption_prediction_lot(api_client,admin_user,users, users_Lots):
    """Verifica que se puede crear una predicción de consumo para un lote."""
    activeUser, _, _ = users
    ActiveUserActiveLot1, _, _ = users_Lots

    prediction = ConsuptionPredictionLot.objects.create(
        user=activeUser,
        lot=ActiveUserActiveLot1,
        period_time="1",
        date_prediction=timezone.now().date(),
        consumption_prediction=123.45,
        code_prediction="TESTCODE123",
        final_date=None,  # Debe calcularse automáticamente en save()
    )
    prediction.refresh_from_db()
    assert prediction.pk is not None
    assert prediction.final_date is not None
    assert prediction.consumption_prediction == 123.45
    assert prediction.code_prediction == "TESTCODE123"
    assert str(prediction).startswith("TESTCODE123")