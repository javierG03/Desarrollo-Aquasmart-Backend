import pytest
import time
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser, Otp, PersonType, DocumentType, UserUpdateLog
from rest_framework.authtoken.models import Token
from django.db.utils import OperationalError
from unittest.mock import patch
from django.utils.timezone import now, timedelta

# ===================== Fixtures =====================

@pytest.fixture
def api_client():
    """Cliente API para realizar solicitudes de prueba."""
    return APIClient()

@pytest.fixture
def person_type(db):
    """Crea un tipo de persona para usar en los tests."""
    return PersonType.objects.create(typeName="Natural")

@pytest.fixture
def another_person_type(db):
    """Crea otro tipo de persona para actualizaciones."""
    return PersonType.objects.create(typeName="Jurídica")

@pytest.fixture
def document_type(db):
    """Crea un tipo de documento para usar en los tests."""
    return DocumentType.objects.create(typeName="Cédula")

@pytest.fixture
def admin_user(db, person_type, document_type):
    """Crea un usuario administrador de prueba."""
    return CustomUser.objects.create_superuser(
        document="admin123",
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone="1234567890",
        address="Admin Address",
        password="AdminPass123",
        person_type=person_type,
        document_type=document_type,
        is_active=True,
        is_registered=True,
    )

@pytest.fixture
def regular_user(db, person_type, document_type):
    """Crea un usuario regular para actualizar."""
    return CustomUser.objects.create_user(
        document="123456789012",
        first_name="John",
        last_name="Doe",
        email="johndoe@example.com",
        phone="1234567890",
        address="Calle 123",
        password="SecurePass123@",
        person_type=person_type,
        document_type=document_type,
        is_active=True,
        is_registered=True,
    )

@pytest.fixture
def another_user(db, person_type, document_type):
    """Crea un segundo usuario para pruebas de duplicidad."""
    return CustomUser.objects.create_user(
        document="987654321098",
        first_name="Jane",
        last_name="Smith",
        email="janesmith@example.com",
        phone="9876543210",
        address="Avenue 456",
        password="SecurePass123@",
        person_type=person_type,
        document_type=document_type,
        is_active=True,
        is_registered=True,
    )

@pytest.fixture
def test_users(db, person_type, document_type):
    """Crea varios usuarios para pruebas de listado."""
    users = []
    for i in range(5):
        user = CustomUser.objects.create_user(
            document=f"12345{i}67890",
            first_name=f"User{i}",
            last_name=f"Test{i}",
            email=f"user{i}@example.com",
            phone=f"123456789{i}",
            address=f"Address {i}",
            password="UserPass123@",
            person_type=person_type,
            document_type=document_type,
            is_active=True,
            is_registered=True,
        )
        users.append(user)
    return users

@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """Cliente API autenticado como administrador."""
    token, _ = Token.objects.get_or_create(user=admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client

# ===================== Tests de Listado y Acceso =====================

@pytest.mark.django_db
class TestUserListingAndAccess:
    """Pruebas para la visualización y acceso a usuarios del distrito."""
    
    def test_list_users_admin_access(self, authenticated_admin_client, test_users):
        """Test de listado de usuarios para administrador autorizado."""
        url = reverse("customuser-list")
        response = authenticated_admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Verificar que se obtienen al menos tantos usuarios como se crearon
        assert len(response.data) >= len(test_users)
        
        # Verificar que la respuesta contiene campos básicos
        for user_data in response.data:
            assert "document" in user_data
            assert "first_name" in user_data
            assert "last_name" in user_data
            assert "email" in user_data
    
    def test_list_users_unauthorized_access(self, api_client):
        """Test de restricción de acceso para usuarios no autorizados."""
        url = reverse("customuser-list")
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data
        assert "credenciales" in response.data["detail"].lower()
    
    def test_user_details_access(self, authenticated_admin_client, regular_user):
        """Test de acceso a detalles de un usuario específico."""
        url = reverse("user-details", kwargs={"document": regular_user.document})
        response = authenticated_admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["document"] == regular_user.document
        assert response.data["first_name"] == regular_user.first_name
        assert response.data["last_name"] == regular_user.last_name
        assert response.data["email"] == regular_user.email

# ===================== Tests de Flujo de Actualización =====================

@pytest.mark.django_db
class TestUserUpdateFlow:
    """Pruebas para el flujo completo de actualización de usuarios."""
    
    def test_complete_flow_positive(self, authenticated_admin_client, regular_user, another_person_type):
        """Test del flujo completo positivo de actualización."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        update_data = {
            "first_name": "John Updated",
            "last_name": "Doe Updated",
            "email": "johndoe.updated@example.com",
            "phone": "9876543210",
            "person_type": another_person_type.personTypeId
        }
        
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "success" in response.data["status"]
        assert "Usuario actualizado exitosamente" in response.data["message"]
        
        # Verificar actualización en la base de datos
        regular_user.refresh_from_db()
        assert regular_user.first_name == "John Updated"
        assert regular_user.last_name == "Doe Updated"
        assert regular_user.email == "johndoe.updated@example.com"
        assert regular_user.phone == "9876543210"
        assert regular_user.person_type.personTypeId == another_person_type.personTypeId
    
    def test_minimal_update(self, authenticated_admin_client, regular_user):
        """Test de actualización con cambios mínimos (solo un campo)."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Actualizar solo el nombre
        update_data = {
            "first_name": "John Modified"
        }
        
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "success" in response.data["status"]
        
        # Verificar que solo el nombre fue actualizado
        regular_user.refresh_from_db()
        assert regular_user.first_name == "John Modified"
        assert regular_user.last_name == "Doe"  # No debe cambiar
        assert regular_user.email == "johndoe@example.com"  # No debe cambiar
    
    def test_cannot_update_document(self, authenticated_admin_client, regular_user):
        """Test de prevención de actualización del número de documento."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        update_data = {
            "document": "999999999999"  # Intentar cambiar el documento
        }
        
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data["status"]
        assert "documento no permitida" in response.data["message"]
        
        # Verificar que el documento no cambió
        regular_user.refresh_from_db()
        assert regular_user.document == "123456789012"  # Documento original
    
    def test_update_unauthorized_user(self, api_client, regular_user):
        """Test de intento de actualización por usuario no autorizado."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        update_data = {
            "first_name": "Unauthorized Update"
        }
        
        response = api_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Verificar que los datos no cambiaron
        regular_user.refresh_from_db()
        assert regular_user.first_name == "John"  # Nombre original
    
    def test_navigation_after_update(self, authenticated_admin_client, regular_user):
        """Test de navegación después de actualización."""
        # Primero actualizar
        update_url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        update_data = {"first_name": "After Navigation"}
        response = authenticated_admin_client.patch(update_url, update_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Luego volver a la lista de usuarios
        list_url = reverse("customuser-list")
        list_response = authenticated_admin_client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK
        
        # Verificar que el usuario actualizado está en la lista
        updated_user_in_list = any(
            user["document"] == regular_user.document and user["first_name"] == "After Navigation"
            for user in list_response.data
        )
        assert updated_user_in_list

# ===================== Tests de Validaciones y Manejo de Errores =====================

@pytest.mark.django_db
class TestValidationsAndErrors:
    """Pruebas para validaciones y manejo de errores en actualización de usuarios."""
    
    def test_email_format_validation(self, authenticated_admin_client, regular_user):
        """Test de validación del formato de correo electrónico."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Correos con formato inválido
        invalid_emails = ["invalid-email", "user@", "@domain.com", "user@domain", "user.com"]
        
        for invalid_email in invalid_emails:
            update_data = {"email": invalid_email}
            response = authenticated_admin_client.patch(url, update_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "email" in str(response.data).lower()
    
    def test_phone_format_validation(self, authenticated_admin_client, regular_user):
        """Test de validación del formato de teléfono."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Teléfonos con formato inválido
        invalid_phones = ["123abc456", "12345", "phone-number"]
        
        for invalid_phone in invalid_phones:
            update_data = {"phone": invalid_phone}
            response = authenticated_admin_client.patch(url, update_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "phone" in str(response.data).lower()
    
    def test_empty_fields_validation(self, authenticated_admin_client, regular_user):
        """Test de validación de campos vacíos."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Campos vacíos (sin incluir 'address' pues no es modificable)
        empty_fields = {
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": ""
        }
        
        for field, value in empty_fields.items():
            update_data = {field: value}
            response = authenticated_admin_client.patch(url, update_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert field in str(response.data).lower() or "este campo" in str(response.data).lower()
    
    def test_duplicate_email(self, authenticated_admin_client, regular_user, another_user):
        """Test de error al intentar usar un correo electrónico que ya existe."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Intentar usar el email de otro usuario
        update_data = {"email": another_user.email}
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data).lower()
        assert "ya está" in str(response.data).lower() or "existe" in str(response.data).lower()
    

    def test_sql_injection_attempt(self, authenticated_admin_client, regular_user):
        """Test de intento de inyección SQL en campos."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        injection_attempts = [
            {"first_name": "Robert'); DROP TABLE users; --"},
            {"email": "attack@example.com'; DELETE FROM auth_user; --"},
            {"last_name": "Smith\" OR 1=1; --"}
        ]
        
        for attempt in injection_attempts:
            response = authenticated_admin_client.patch(url, attempt)
            
            # Debería rechazar estos intentos o sanitizarlos
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST, 
                status.HTTP_200_OK  # Si sanitiza correctamente
            ]
            
            # Verificar que no se ejecutó código malicioso
            assert CustomUser.objects.filter(document=regular_user.document).exists()

# ===================== Tests de Confirmaciones y Casos Especiales =====================

@pytest.mark.django_db
class TestConfirmationsAndSpecialCases:
    """Pruebas para confirmaciones y casos especiales de actualización."""
    
    def test_confirmation_message(self, authenticated_admin_client, regular_user):
        """Test de mensaje de confirmación después de actualización exitosa."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        update_data = {"first_name": "Confirmation Test"}
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "success" in response.data["status"]
        assert "actualizado exitosamente" in response.data["message"].lower()
        assert "data" in response.data
    
    def test_response_time(self, authenticated_admin_client, regular_user):
        """Test de tiempo de respuesta inferior a 5 segundos."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        update_data = {"first_name": "Response Time Test"}
        
        start_time = time.time()
        response = authenticated_admin_client.patch(url, update_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 5.0, f"Tiempo de respuesta ({response_time:.2f}s) excede los 5 segundos"
    
    def test_user_not_found(self, authenticated_admin_client):
        """Test de manejo de error cuando se intenta actualizar un usuario inexistente."""
        nonexistent_document = "999999999999"
        url = reverse("admin-user-update", kwargs={"document": nonexistent_document})
        
        update_data = {"first_name": "Nonexistent User"}
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @patch("rest_framework.authtoken.models.Token.objects.get")
    def test_session_expired(self, mock_token_get, authenticated_admin_client, regular_user):
        """Test de flujo con sesión expirada."""
        # Simular token expirado o inválido
        mock_token_get.side_effect = Token.DoesNotExist
        
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        update_data = {"first_name": "Session Expired Test"}
        
        # Configurar encabezado con token inválido
        authenticated_admin_client.credentials(HTTP_AUTHORIZATION='Token expired_token')
        response = authenticated_admin_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data
        detail = response.data["detail"].lower()
        assert "inválido" in detail or "no se proveyeron" in detail

# ===================== Tests de Flujos Completos (End-to-End) =====================

@pytest.mark.django_db
class TestFlujosCompletos:
    """Pruebas para flujos completos end-to-end."""
    
    def test_full_e2e_flow(self, api_client, admin_user, regular_user, another_person_type):
        """Test del flujo completo de inicio a fin."""
        # 1. Iniciar sesión
        login_url = reverse("login")
        login_data = {"document": admin_user.document, "password": "AdminPass123"}
        login_response = api_client.post(login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK
        
        # 2. Obtener OTP y validarlo
        otp_instance = Otp.objects.filter(user=admin_user, is_login=True).first()
        assert otp_instance is not None
        
        validate_url = reverse("validate-otp")
        otp_data = {"document": admin_user.document, "otp": otp_instance.otp}
        validate_response = api_client.post(validate_url, otp_data)
        assert validate_response.status_code == status.HTTP_200_OK
        assert "token" in validate_response.data
        
        # 3. Usar el token para listar usuarios
        token = validate_response.data["token"]
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        list_url = reverse("customuser-list")
        list_response = api_client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK
        
        # 4. Actualizar un usuario (sin modificar 'address')
        update_url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        update_data = {
            "first_name": "E2E Flow",
            "last_name": "Complete Test",
            "email": "e2e.test@example.com",
            "phone": "5551234567",
            "person_type": another_person_type.personTypeId
        }
        
        update_response = api_client.patch(update_url, update_data)
        assert update_response.status_code == status.HTTP_200_OK
        assert "success" in update_response.data["status"]
        
        # 5. Verificar que los datos fueron actualizados correctamente
        regular_user.refresh_from_db()
        assert regular_user.first_name == "E2E Flow"
        assert regular_user.last_name == "Complete Test"
        assert regular_user.email == "e2e.test@example.com"
        assert regular_user.phone == "5551234567"
        assert regular_user.person_type.personTypeId == another_person_type.personTypeId
        
        # 6. Cerrar sesión
        logout_url = reverse("logout")
        logout_response = api_client.post(logout_url)
        assert logout_response.status_code == status.HTTP_200_OK
        
        # 7. Verificar que el token ya no funciona
        list_response_after_logout = api_client.get(list_url)
        assert list_response_after_logout.status_code == status.HTTP_401_UNAUTHORIZED

# ===================== Tests de Validaciones por Campo =====================

@pytest.mark.django_db
class TestFieldValidations:
    """Pruebas específicas para validaciones de cada campo modificable."""
    
    def test_first_name_validations(self, authenticated_admin_client, regular_user):
        """Test de validaciones específicas para el campo nombre."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación de longitud máxima (20 caracteres)
        long_name = "A" * 21  # 21 caracteres (excede el límite)
        response = authenticated_admin_client.patch(url, {"first_name": long_name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "first_name" in str(response.data).lower()
        
        # Validación de campo vacío
        empty_name = ""
        response = authenticated_admin_client.patch(url, {"first_name": empty_name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "first_name" in str(response.data).lower()
        
        # Validación con valor válido
        valid_name = "John Modified"
        response = authenticated_admin_client.patch(url, {"first_name": valid_name})
        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.first_name == valid_name
    
    def test_last_name_validations(self, authenticated_admin_client, regular_user):
        """Test de validaciones específicas para el campo apellido."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación de longitud máxima (20 caracteres)
        long_last_name = "B" * 21  # 21 caracteres (excede el límite)
        response = authenticated_admin_client.patch(url, {"last_name": long_last_name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "last_name" in str(response.data).lower()
        
        # Validación de campo vacío
        empty_last_name = ""
        response = authenticated_admin_client.patch(url, {"last_name": empty_last_name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "last_name" in str(response.data).lower()
        
        # Validación con valor válido
        valid_last_name = "Doe Modified"
        response = authenticated_admin_client.patch(url, {"last_name": valid_last_name})
        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.last_name == valid_last_name
    
    def test_email_validations(self, authenticated_admin_client, regular_user, another_user):
        """Test de validaciones específicas para el campo correo electrónico."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación de formato inválido
        invalid_emails = [
            "plainaddress",
            "user@domain",
            "@example.com",
            "user.example.com"
        ]
        for invalid_email in invalid_emails:
            response = authenticated_admin_client.patch(url, {"email": invalid_email})
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "email" in str(response.data).lower()
        
        # Validación de longitud máxima (50 caracteres)
        long_email = f"{'a' * 40}@example.com"  # Email con más de 50 caracteres
        response = authenticated_admin_client.patch(url, {"email": long_email})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data).lower()
        
        # Validación de duplicidad
        duplicate_email = another_user.email
        response = authenticated_admin_client.patch(url, {"email": duplicate_email})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data).lower()
        
        # Validación de campo vacío
        empty_email = ""
        response = authenticated_admin_client.patch(url, {"email": empty_email})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data).lower()
        
        # Validación con valor válido
        valid_email = "valid.email@example.com"
        response = authenticated_admin_client.patch(url, {"email": valid_email})
        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.email == valid_email
    
    def test_phone_validations(self, authenticated_admin_client, regular_user):
        """Test de validaciones específicas para el campo teléfono."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación de caracteres no numéricos
        non_numeric_phone = "123abc4567"
        response = authenticated_admin_client.patch(url, {"phone": non_numeric_phone})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in str(response.data).lower()
        
        # Validación de longitud (debe ser exactamente 10 dígitos)
        short_phone = "123456"  # Menos de 10 dígitos
        response = authenticated_admin_client.patch(url, {"phone": short_phone})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in str(response.data).lower()
        
        long_phone = "12345678901"  # Más de 10 dígitos
        response = authenticated_admin_client.patch(url, {"phone": long_phone})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in str(response.data).lower()
        
        # Validación de campo vacío
        empty_phone = ""
        response = authenticated_admin_client.patch(url, {"phone": empty_phone})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in str(response.data).lower()
        
        # Validación con valor válido (exactamente 10 dígitos)
        valid_phone = "1234567890"
        response = authenticated_admin_client.patch(url, {"phone": valid_phone})
        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.phone == valid_phone
    
    def test_person_type_validations(self, authenticated_admin_client, regular_user, another_person_type):
        """Test de validaciones específicas para el campo tipo de persona."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación con ID de tipo de persona inexistente
        nonexistent_person_type = 9999
        response = authenticated_admin_client.patch(url, {"person_type": nonexistent_person_type})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "person_type" in str(response.data).lower()
        
        # Validación con ID inválido (no numérico)
        invalid_person_type = "abc"
        response = authenticated_admin_client.patch(url, {"person_type": invalid_person_type})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "person_type" in str(response.data).lower()
        
        # Validación con valor válido
        valid_person_type = another_person_type.personTypeId
        response = authenticated_admin_client.patch(url, {"person_type": valid_person_type})
        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.person_type.personTypeId == valid_person_type
    
    @pytest.mark.skip("Prueba no aplicable si no se implementa la carga de archivos en AdminUserUpdateAPIView")
    def test_file_attachment_validations(self, authenticated_admin_client, regular_user):
        """Test de validaciones específicas para anexos/archivos."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Preparar un archivo de prueba con tamaño > 500KB
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Archivo demasiado grande (> 500KB)
        large_file_content = io.BytesIO(b'x' * 600 * 1024)  # 600KB
        large_file = SimpleUploadedFile("large_doc.pdf", large_file_content.read(), content_type="application/pdf")
        
        response = authenticated_admin_client.patch(
            url, 
            {"files": large_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in str(response.data).lower() or "anexo" in str(response.data).lower()
        
        # Archivo con tipo incorrecto (no PDF)
        invalid_type_content = io.BytesIO(b'test content')
        invalid_file = SimpleUploadedFile("doc.txt", invalid_type_content.read(), content_type="text/plain")
        
        response = authenticated_admin_client.patch(
            url, 
            {"files": invalid_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in str(response.data).lower() or "anexo" in str(response.data).lower()
        
        # Archivo válido (PDF, < 500KB)
        valid_file_content = io.BytesIO(b'x' * 100 * 1024)  # 100KB
        valid_file = SimpleUploadedFile("valid_doc.pdf", valid_file_content.read(), content_type="application/pdf")
        
        response = authenticated_admin_client.patch(
            url, 
            {"files": valid_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_role_validations(self, authenticated_admin_client, regular_user):
        """Test de validaciones específicas para el tipo de rol del usuario."""
        from django.contrib.auth.models import Group
        
        # Crear algunos grupos para las pruebas
        admin_group = Group.objects.create(name="Administradores")
        user_group = Group.objects.create(name="Usuarios")
        
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Validación con ID de grupo inexistente
        nonexistent_group = 9999
        response = authenticated_admin_client.patch(url, {"groups": [nonexistent_group]})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "group" in str(response.data).lower()
        
        # Validación con valor válido
        valid_group = admin_group.id
        response = authenticated_admin_client.patch(url, {"groups": [valid_group]})
        
        # Verificar si la implementación actual admite actualización de grupos
        if response.status_code == status.HTTP_200_OK:
            regular_user.refresh_from_db()
            assert admin_group in regular_user.groups.all()
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_no_changes_validation(self, authenticated_admin_client, regular_user):
        """Test que verifica que se rechaza la actualización sin cambios."""
        url = reverse("admin-user-update", kwargs={"document": regular_user.document})
        
        # Enviar los mismos datos actuales sin modificar (sin 'address')
        current_data = {
            "first_name": regular_user.first_name,
            "last_name": regular_user.last_name,
            "email": regular_user.email,
            "phone": regular_user.phone,
            "person_type": regular_user.person_type.personTypeId
        }
        
        response = authenticated_admin_client.patch(url, current_data)
        
        # Dependiendo de la implementación, podría rechazar esta actualización
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert "cambios" in str(response.data).lower() or "modificar" in str(response.data).lower()
        else:
            assert response.status_code == status.HTTP_200_OK
            assert "no se detectaron cambios" in str(response.data).lower()
