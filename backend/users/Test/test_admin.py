import pytest
from django.contrib.auth.models import Group
from django.contrib.admin.sites import site
from django.urls import reverse
from django.test import Client
from users.models import CustomUser, DocumentType, PersonType
from users.admin import CustomUserAdmin


@pytest.mark.django_db
def test_admin_registration():
    """ Verifica que los modelos están registrados en el admin """
    assert site.is_registered(CustomUser)
    assert site.is_registered(DocumentType)
    assert site.is_registered(PersonType)

@pytest.mark.django_db
def test_admin_list_display():
    """ Verifica que CustomUserAdmin tenga los campos correctos en list_display """
    admin_instance = CustomUserAdmin(CustomUser, site)
    expected_fields = ('document', 'document_type', 'person_type', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'date_joined', 'last_login', 'display_groups')
    assert admin_instance.list_display == expected_fields

@pytest.mark.django_db
def test_admin_search_fields():
    """ Verifica que los campos de búsqueda están configurados correctamente """
    admin_instance = CustomUserAdmin(CustomUser, site)
    expected_fields = ('document', 'email', 'first_name', 'last_name', 'document_type', 'person_type')
    assert admin_instance.search_fields == expected_fields

@pytest.mark.django_db
def test_display_groups():
    """ Prueba que la función display_groups devuelva los nombres de los grupos correctamente """
    user = CustomUser.objects.create(document="12345678", first_name="Test", last_name="User", email="test@example.com", phone="1234567890") # Added phone
    group1 = Group.objects.create(name="Admin")
    group2 = Group.objects.create(name="User")
    user.groups.add(group1, group2)

    admin_instance = CustomUserAdmin(CustomUser, site)
    assert admin_instance.display_groups(user) == "Admin, User"