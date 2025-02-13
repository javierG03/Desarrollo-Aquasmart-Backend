import pytest
from users.doc_serializers import LoginSerializer, LoginResponseSerializer
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

def test_login_serializer_valid_data():
    """Prueba que LoginSerializer valide correctamente los datos."""
    data = {"document": "123456789", "password": "password123"}
    serializer = LoginSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

def test_login_serializer_missing_fields():
    """Prueba que LoginSerializer falle cuando faltan campos."""
    data = {"document": "123456789"}  # Falta la contraseña
    serializer = LoginSerializer(data=data)
    with pytest.raises(ValidationError):
        serializer.is_valid(raise_exception=True)

def test_login_response_serializer():
    """Prueba que LoginResponseSerializer maneje correctamente los tokens."""
    data = {"refresh": "refresh_token_example", "access": "access_token_example"}
    serializer = LoginResponseSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data
