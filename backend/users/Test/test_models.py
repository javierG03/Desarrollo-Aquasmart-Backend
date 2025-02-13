import pytest
from django.utils import timezone
from users.models import CustomUser, Otp, LoginHistory, DocumentType, PersonType

def test_create_user(db):
    user = CustomUser.objects.create_user(
        document="123456789",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="1234567890",
        password="securepassword",
        address="Calle 123"
    )
    assert user.document == "123456789"
    assert user.check_password("securepassword")

def test_create_superuser(db):
    admin = CustomUser.objects.create_superuser(
        document="987654321",
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone="0987654321",
        password="supersecurepassword",
        address="Avenida Principal"
    )
    assert admin.is_staff is True
    assert admin.is_superuser is True

def test_generate_otp(db):
    user = CustomUser.objects.create_user(
        document="111222333",
        first_name="Carlos",
        last_name="Gomez",
        email="carlos@example.com",
        phone="1122334455",
        password="password123",
        address="Calle 456"
    )
    otp_instance = Otp.objects.create(user=user)
    otp_instance.generateOTP()
    assert len(otp_instance.otp) == 6
    assert otp_instance.otp.isdigit()

def test_validate_otp(db):
    user = CustomUser.objects.create_user(
        document="555666777",
        first_name="Ana",
        last_name="Torres",
        email="ana@example.com",
        phone="5566778899",
        password="mypassword",
        address="Avenida 789"
    )
    otp_instance = Otp.objects.create(user=user)
    otp_instance.generateOTP()
    assert otp_instance.validateOTP() is True
    otp_instance.creation_time = timezone.now() - timezone.timedelta(minutes=16)
    assert otp_instance.validateOTP() is False

def test_login_history_creation(db):
    user = CustomUser.objects.create_user(
        document="333444555",
        first_name="María",
        last_name="López",
        email="maria@example.com",
        phone="3344556677",
        password="password456",
        address="Calle 789"
    )
    login_record = LoginHistory.objects.create(user=user)
    assert login_record.user == user
    assert login_record.timestamp <= timezone.now()

def test_create_document_type(db):
    doc_type = DocumentType.objects.create(typeName="Cédula de Ciudadanía")
    assert doc_type.typeName == "Cédula de Ciudadanía"

def test_create_person_type(db):
    person_type = PersonType.objects.create(typeName="Natural")
    assert person_type.typeName == "Natural"
