import pytest
from django.contrib.auth.models import Group
from django.contrib.admin.sites import site
from django.urls import reverse
from django.test import Client
from users.models import CustomUser, DocumentType, PersonType
from users.admin import CustomUserAdmin

import pytest
from users.models import CustomUser

@pytest.mark.django_db
def test_admin_login(client):
    """ Prueba que un usuario admin pueda acceder al panel de administración """
    admin_user = CustomUser.objects.create_superuser(
    document="admin123",
    first_name="Admin",
    last_name="User",
    address="Calle 123",
    email="admin@example.com",
    phone="1234567890",
    password="password123"
    )
    
    assert admin_user.is_staff is True  
    assert admin_user.is_superuser is True  
    assert admin_user.is_active is True  

    # Django usa `document` como `USERNAME_FIELD`, por lo que debe pasarse en `client.login`
    logged_in = client.login(document="admin123", password="password123")
    assert logged_in  
