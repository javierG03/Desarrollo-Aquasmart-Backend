import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.test import Client
from users.models import CustomUser, DocumentType, PersonType
import pytest
from users.models import CustomUser, Otp, DocumentType, PersonType
from django.utils import timezone

@pytest.mark.django_db
class TestCustomUserModel:
    
    @pytest.fixture
    def create_document_type(self):
        return DocumentType.objects.create(typeName="Cédula")

    @pytest.fixture
    def create_person_type(self):
        return PersonType.objects.create(typeName="Natural")

    @pytest.fixture
    def create_user(self, create_document_type, create_person_type):
        return CustomUser.objects.create_user(
            document="123456789",
            first_name="Oscar",
            last_name="Perdomo",
            email="oscar@example.com",
            phone="1234567890",
            password="password123",
            address="Calle 123",
            document_type=create_document_type,
            person_type=create_person_type
        )

    def test_create_user(self, create_user):
        user = create_user
        assert user.document == "123456789"
        assert user.first_name == "Oscar"
        assert user.last_name == "Perdomo"
        assert user.email == "oscar@example.com"
        assert user.phone == "1234567890"
        assert user.isRegistered is False
        assert user.check_password("password123") is True

@pytest.mark.django_db
class TestOtpModel:

    @pytest.fixture
    def create_user(self, create_document_type, create_person_type):
        return CustomUser.objects.create_user(
            document="123456789",
            first_name="Oscar",
            last_name="Perdomo",
            email="oscar@example.com",
            phone="1234567890",
            password="password123",
            address="Calle 123",
            document_type=create_document_type,
            person_type=create_person_type
        )

