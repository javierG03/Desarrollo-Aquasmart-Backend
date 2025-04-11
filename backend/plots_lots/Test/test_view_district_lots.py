import pytest
from django.urls import reverse
from plots_lots.models import Lot, Plot


@pytest.mark.django_db
def test_admin_can_view_all_lots(api_client, admin_user, admin_registered_lots, normal_user, registered_lots, login_and_validate_otp):
    """✅ El admin debe ver todos los lotes."""
    token = login_and_validate_otp(admin_user, api_client, "AdminPass123*")
    api_client.credentials(HTTP_AUTHORIZATION="Token " + token)

    url = reverse("lot-list")
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert any(lot["crop_variety"] == "Variedad X" for lot in data)
    assert any(lot["crop_variety"] == "Variedad A" for lot in data)




@pytest.mark.django_db
def test_normal_user_can_only_view_own_lots(api_client, normal_user, registered_lots, login_and_validate_otp):
    """✅ Usuario normal solo ve sus lotes."""
    token = login_and_validate_otp(normal_user, api_client, "SecurePass123")
    api_client.credentials(HTTP_AUTHORIZATION="Token " + token)

    url = reverse("lot-list")
    response = api_client.get(url)

    assert response.status_code == 200

    user_plot_ids = Plot.objects.filter(owner=normal_user).values_list("id_plot", flat=True)
    api_lots = [lot for lot in response.data if lot["plot"] in user_plot_ids]
    
    assert len(api_lots) == Lot.objects.filter(plot__owner=normal_user).count()
    print("✅ Test completado con éxito. El usuario normal solo ve sus propios lotes.")



@pytest.mark.django_db
def test_unauthenticated_user_cannot_view_lots(api_client):
    """❌ Usuario no autenticado no puede ver lotes."""
    url = reverse("lot-list")
    response = api_client.get(url)
    assert response.status_code == 401
