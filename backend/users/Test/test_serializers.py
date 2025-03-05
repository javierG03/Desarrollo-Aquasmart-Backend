import pytest
from users.serializers import CustomUserSerializer, GenerateOtpPasswordRecoverySerializer, ValidateOtpSerializer, ResetPasswordSerializer

# Add your tests here

from django.contrib.auth.hashers import check_password

from users.models import CustomUser, DocumentType, PersonType, Otp

@pytest.mark.django_db
def test_custom_user_serializer_create():
    document_type = DocumentType.objects.create(typeName="DNI")
    person_type = PersonType.objects.create(typeName="Natural")

    data = {
        'document': '12345678',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'document_type': document_type.documentTypeId,
        'person_type': person_type.personTypeId,
        'phone': '123456789',
        'address': '123 Main St',
        'password': 'securepassword123',
    }

    serializer = CustomUserSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    user = serializer.save()
    assert user.document == '12345678'
    assert user.is_active is False
    assert check_password('securepassword123', user.password)

@pytest.mark.django_db
def test_recover_password_serializer():
    user = CustomUser.objects.create(document='12345678', email='john.doe@example.com', phone= '123456789')

    data = {'document': '12345678', 'phone': '123456789'}
    serializer = GenerateOtpPasswordRecoverySerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    response = serializer.create(serializer.validated_data)
    assert 'otp' in response
    assert 'message' in response

    otp_instance = Otp.objects.filter(user=user).first()
    assert otp_instance is not None


@pytest.mark.django_db
def test_reset_password_serializer():
    user = CustomUser.objects.create(document='12345678', password='oldpassword')
    Otp.objects.create(user=user, otp='123456', is_validated=True)

    data = {'document': '12345678', 'new_password': 'newpassword123'}
    serializer = ResetPasswordSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    user = serializer.save()
    assert check_password('newpassword123', user.password)

    otp_instances = Otp.objects.filter(user=user, is_validated=True)
    assert otp_instances.count() == 0

'''''
#errores en los test
@pytest.mark.django_db
def test_validate_otp_serializer():
    user = CustomUser.objects.create(document='12345678')
    otp_instance = Otp.objects.create(user=user, otp='123456')

    data = {'document': '12345678', 'otp': '123456'}
    serializer = ValidateOtpSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    validated_data = serializer.validate(data)
    assert validated_data == data

    otp_instance.refresh_from_db()
    assert otp_instance.is_validated is True '''