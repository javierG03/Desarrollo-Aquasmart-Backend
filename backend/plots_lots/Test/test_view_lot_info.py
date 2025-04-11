import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from plots_lots.models import Lot, SoilType, Plot, CropType
from users.models import CustomUser
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Cliente API para realizar solicitudes de prueba."""
    return APIClient()




@pytest.mark.django_db
def test_admin_can_view_all_lots(api_client):
    admin = CustomUser.objects.create_superuser(
        document="123456789012",
        password="Admin123*",
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone="3209999999",
        is_staff=True  # <- Este es el campo real en vez de is_stage
    )
    token = Token.objects.create(user=admin)
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    user = CustomUser.objects.create_user(
        document="123456789013",
        password="Password123**",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="3210000000"
    )

    plot = Plot.objects.create(
        plot_name="Parcela Uno",
        owner=user,
        latitud=4.1234,
        longitud=-74.1234,
        plot_extension=5.0
    )

    crop_type = CropType.objects.create(name="Trigo")
    soil_type = SoilType.objects.create(name="Franco")

    Lot.objects.create(
        plot=plot,
        crop_name="Lote Admin",
        crop_type=crop_type,
        crop_variety="Variedad T",
        soil_type=soil_type
    )

    url = reverse("lot-list")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert any(lot["crop_variety"] == "Variedad T" for lot in data)



@pytest.mark.django_db
def test_normal_user_can_only_view_own_lots(api_client):
    user = CustomUser.objects.create_user(
        document="123456789013",
        password="Password123**",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="3210000000"
    )
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    plot = Plot.objects.create(
        plot_name="Parcela Uno",
        owner=user,
        latitud=4.1234,
        longitud=-74.1234,
        plot_extension=5.0
    )

    crop_type = CropType.objects.create(name="Maíz")
    soil_type = SoilType.objects.create(name="Arcilloso")

    Lot.objects.create(
        plot=plot,
        crop_name="Lote A",
        crop_type=crop_type,
        crop_variety="Variedad A",
        soil_type=soil_type
    )

    url = reverse("lot-list")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert any(lot["crop_variety"] == "Variedad A" for lot in data)



@pytest.mark.django_db
def test_normal_user_cannot_view_other_users_lots(api_client):
    user1 = CustomUser.objects.create_user(
        document="123456789014",
        password="Password123**",
        first_name="Juanito",
        last_name="Pérez",
        email="Juanito@example.com",
        phone="0000123456"
    )
    user2 = CustomUser.objects.create_user(
        document="123456789015",
        password="Password456*",
        first_name="Angel",
        last_name="Pérez",
        email="Angel@example.com",
        phone="1234567888"
    )
    token = Token.objects.create(user=user1)
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    plot = Plot.objects.create(
        plot_name="Parcela Uno",
        owner=user2,  # <- Propietario es otro usuario
        latitud=4.1234,
        longitud=-74.1234,
        plot_extension=5.0
    )

    crop_type = CropType.objects.create(name="Maíz")
    soil_type = SoilType.objects.create(name="Arcilloso")

    Lot.objects.create(
        plot=plot,
        crop_name="Lote A",
        crop_type=crop_type,
        crop_variety="Variedad A",
        soil_type=soil_type
    )

    url = reverse("lot-list")
    response = api_client.get(url)
    assert response.status_code == 200
    assert b"Lote A" not in response.content


@pytest.mark.django_db
def test_unauthenticated_user_cannot_view_lot_info(api_client):
    url = reverse("lot-list")
    response = api_client.get(url)
    assert response.status_code == 401  # No autenticado