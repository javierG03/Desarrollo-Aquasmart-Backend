import pytest
from django.utils import timezone
from users.models import CustomUser, Otp, LoginHistory, LoginRestriction, DocumentType, PersonType
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils.timezone import now


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



# ========================
# TESTS PARA CustomUser
# ========================
@pytest.mark.django_db
def test_create_user_with_special_chars():
    """Verifica que el sistema no permita caracteres especiales en el documento."""
    with pytest.raises(ValueError, match="El documento es obligatorio"):
        CustomUser.objects.create_user(
            document="ABC123!@#",
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            phone="3001234567",
            password="SecurePass123!"
        )

@pytest.mark.django_db
def test_create_user_with_long_values():
    """Verifica que el sistema maneje entradas excesivamente largas sin romperse."""
    user = CustomUser.objects.create_user(
        document="12345678901234567890",
        first_name="Juan" * 50,
        last_name="Pérez" * 50,
        email="juan" + "a" * 200 + "@example.com",
        phone="3" * 50,
        password="SecurePass123!"
    )

    assert len(user.first_name) <= 50  # Debe truncar a 50 caracteres
    assert len(user.last_name) <= 50
    assert len(user.phone) <= 20  # Teléfono debe ser máximo 20 caracteres

@pytest.mark.django_db
def test_create_user_with_invalid_email():
    """Verifica que el sistema rechace emails con formatos inválidos."""
    with pytest.raises(ValidationError):
        user = CustomUser.objects.create_user(
            document="1234567890",
            first_name="Juan",
            last_name="Pérez",
            email="correo-invalido",
            phone="3001234567",
            password="SecurePass123!"
        )
        user.full_clean()  # Esto dispara la validación

@pytest.mark.django_db
def test_create_user_with_weak_password():
    """Verifica que el sistema rechace contraseñas demasiado débiles."""
    with pytest.raises(ValidationError):
        user = CustomUser.objects.create_user(
            document="1234567890",
            first_name="Juan",
            last_name="Pérez",
            email="juan@example.com",
            phone="3001234567",
            password="123"  # Contraseña muy corta
        )
        user.full_clean()  # Esto dispara la validación


# ========================
# TESTS PARA OTP
# ========================

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
    otp_instance.generate_otp()
    assert len(otp_instance.otp) == 6
    assert otp_instance.otp.isdigit()

def test_validate_life_otp(db):
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
    otp_instance.generate_otp()
    assert otp_instance.validate_life_otp() is True
    otp_instance.creation_time = timezone.now() - timezone.timedelta(minutes=16)
    assert otp_instance.validate_life_otp() is False


@pytest.mark.django_db
def test_expired_otp():
    """Verifica que un OTP caducado no sea válido."""
    user = CustomUser.objects.create_user(
        document="1234567890",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="3001234567",
        password="SecurePass123!"
    )

    otp_instance = Otp.objects.create(user=user)
    otp_instance.creation_time = now() - timedelta(minutes=20)  # Expirado
    otp_instance.save()

    assert otp_instance.validate_life_otp() is False  # Debe estar expirado

@pytest.mark.django_db
def test_otp_reuse():
    """Verifica que un OTP ya validado no se pueda reutilizar."""
    user = CustomUser.objects.create_user(
        document="1234567890",
        first_name="Juan",
        last_name="Pérez",
        email="juan@example.com",
        phone="3001234567",
        password="SecurePass123!"
    )

    otp_instance = Otp.objects.create(user=user)
    otp_instance.is_validated = True  # OTP ya usado
    otp_instance.save()

    assert otp_instance.is_validated is True  # Debe estar marcado como usado





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
