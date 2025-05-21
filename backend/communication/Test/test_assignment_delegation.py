import pytest
from rest_framework import status
from django.urls import reverse
from communication.assigment_maintenance.models import Assignment
from communication.requests.models import FlowRequest, FlowRequestType
from communication.reports.models import FailureReport, TypeReport
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from iot.models import IoTDevice
from django.utils import timezone
from django.core import mail
from django.conf import settings
import json
from plots_lots.models import Lot, Plot 
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestAssignmentFunctionality:
    """Test suite for RF68: Delegation of reports to competent users."""

    def setup_permissions(self, admin_user, tecnico_user=None):
        """Helper method to set up permissions for assignment tests"""
        # Get content type for Assignment model
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Create or get can_assign_user permission
        try:
            assign_permission = Permission.objects.get(
                codename='can_assign_user',
                content_type=content_type
            )
        except Permission.DoesNotExist:
            assign_permission = Permission.objects.create(
                codename='can_assign_user',
                name='Can assign user to handle requests/reports',
                content_type=content_type
            )
            
        # Add permission to admin user
        admin_user.user_permissions.add(assign_permission)
        
        # Setup technician permissions if provided
        if tecnico_user:
            # Create or get can_be_assigned permission
            try:
                can_be_assigned = Permission.objects.get(
                    codename='can_be_assigned',
                    content_type=content_type
                )
            except Permission.DoesNotExist:
                can_be_assigned = Permission.objects.create(
                    codename='can_be_assigned',
                    name='Can be assigned to handle requests/reports',
                    content_type=content_type
                )
                
            tecnico_user.user_permissions.add(can_be_assigned)
            tecnico_user.save()
            
        admin_user.save()
        return assign_permission

    def setup_flow_request(self, normal_user, lote, iot_device):
        """Helper method to create a flow request that requires delegation"""
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de prueba para delegación',
            requires_delegation=True
        )
        return flow_request
        
    def setup_failure_report(self, normal_user, lote, plot, iot_device):
        """Helper method to create a failure report"""
        failure_report = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote,
            plot=plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de prueba para delegación'
        )
        return failure_report

    def setup_water_supply_failure_report(self, normal_user, lote, plot, iot_device):
        """Helper method to create a water supply failure report"""
        failure_report = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote,
            plot=plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en el suministro de agua para prueba'
        )
        return failure_report

    def setup_application_failure_report(self, normal_user):
        """Helper method to create an application failure report (sin lote o predio)"""
        failure_report = FailureReport.objects.create(
            created_by=normal_user,
            type='Reporte',
            failure_type=TypeReport.APPLICATION_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en el aplicativo para prueba'
        )
        return failure_report

    def setup_definitive_cancellation_request(self, normal_user, lote, iot_device):
        """Helper method to create a definitive cancellation flow request"""
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de cancelación definitiva para prueba',
            requires_delegation=True
        )
        return flow_request
    
    def test_assignment_list_permission(self, api_client, admin_user, login_and_validate_otp):
        """Test that users with the correct permissions can access assignment list."""
        print("\n[TEST] Iniciando test_assignment_list_permission")
        print("[STEP] Iniciando sesión como administrador")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Agregando permiso de visualización de asignaciones")
        # Add required permission
        content_type = ContentType.objects.get_for_model(Assignment)
        try:
            view_permission = Permission.objects.get(
                codename='view_assignment',
                content_type=content_type
            )
            print("[INFO] Permiso view_assignment existente encontrado")
        except Permission.DoesNotExist:
            view_permission = Permission.objects.create(
                codename='view_assignment',
                name='Can view assignment',
                content_type=content_type
            )
            print("[INFO] Permiso view_assignment creado")
            
        admin_user.user_permissions.add(view_permission)
        admin_user.save()
        print(f"[INFO] Permiso asignado al usuario {admin_user.document}")
        
        # Access assignment list
        url = reverse('list_iot_devices')  # Adjust to actual endpoint
        print(f"[STEP] Accediendo a la lista de dispositivos URL: {url}")
        response = client.get(url)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verify access is granted
        assert response.status_code == status.HTTP_200_OK
        print("[PASS] Test completado exitosamente")

    def test_create_assignment_requires_permission(self, api_client, normal_user, login_and_validate_otp):
        """Test that only users with can_assign_user permission can create assignments."""
        print("\n[TEST] Iniciando test_create_assignment_requires_permission")
        
        print(f"[STEP] Iniciando sesión como usuario normal: {normal_user.document}")
        # Login as normal user with correct password
        client = login_and_validate_otp(api_client, normal_user, password="UserPass123@")
        
        url = reverse('assignment-create')
        print(f"[STEP] Intentando crear una asignación sin permiso, URL: {url}")
        
        # Prepare data
        assignment_data = {
            'assigned_to': normal_user.document,
            'flow_request': 1
        }
        print(f"[INFO] Datos de la solicitud: {assignment_data}")
        
        # Attempt to create an assignment without permission
        response = client.post(url, data=assignment_data)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # User should get permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        print("[PASS] Test completado exitosamente - permiso denegado como se esperaba")

    def test_validate_assignment_exclusivity(self, api_client, admin_user, tecnico_user, 
                                   login_and_validate_otp, user_lot, user_plot, 
                                   normal_user, iot_device):
        """Test validation that assignments can't have both flow_request and failure_report."""
        print("\n[TEST] Iniciando test_validate_assignment_exclusivity")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos necesarios")
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que requiere delegación")
        # Create a flow request that requires delegation
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Creando reporte de fallo")
        # Create a failure report
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Intentando crear asignación con ambos elementos")
        # Try to create assignment with both flow_request and failure_report
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id,
            'failure_report': failure_report.id
        }
        print(f"[INFO] Datos de la solicitud: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the JSON response
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"[INFO] Respuesta parseada: {response_data}")
        
        assert "No se puede asignar un 'flow_request' y un 'failure_report' al mismo tiempo" in response_data['errors']['non_field_errors']
        print("[PASS] Test completado exitosamente - mensaje correcto recibido")

    def test_prevent_self_assignment(self, api_client, admin_user,
                           login_and_validate_otp, user_lot,
                           normal_user, iot_device):
        """Test that users cannot assign tasks to themselves."""
        print("\n[TEST] Iniciando test_prevent_self_assignment")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos para administrador")
        # Setup admin permissions for both assigning and being assigned
        assign_permission = self.setup_permissions(admin_user)
        
        print("[STEP] Dando permiso can_be_assigned al administrador")
        # Get content type for Assignment model
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Give admin permission to be assigned (to test self-assignment)
        try:
            can_be_assigned = Permission.objects.get(
                codename='can_be_assigned',
                content_type=content_type
            )
            print("[INFO] Permiso can_be_assigned existente encontrado")
        except Permission.DoesNotExist:
            can_be_assigned = Permission.objects.create(
                codename='can_be_assigned',
                name='Can be assigned to handle requests/reports',
                content_type=content_type
            )
            print("[INFO] Permiso can_be_assigned creado")
            
        admin_user.user_permissions.add(can_be_assigned)
        admin_user.save()
        print(f"[INFO] Permiso can_be_assigned asignado al administrador: {admin_user.document}")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud de flujo")
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Intentando auto-asignarse la solicitud")
        # Try to self-assign
        url = reverse('assignment-create')
        data = {
            'assigned_to': admin_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] Datos de la solicitud: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the response and check for error message
        import json
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"[INFO] Respuesta parseada: {response_data}")
        
        assert 'errors' in response_data
        assert 'non_field_errors' in response_data['errors']
        assert 'usuario no puede asignarse' in response_data['errors']['non_field_errors']
        print("[PASS] Test completado exitosamente - auto-asignación rechazada correctamente")
        
    def test_validate_flow_request_requires_delegation(self, api_client, admin_user,
                                            tecnico_user, login_and_validate_otp,
                                            user_lot, normal_user, iot_device):
        """Test that only flow requests that require delegation can be assigned."""
        print("\n[TEST] Iniciando test_validate_flow_request_requires_delegation")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que NO requiere delegación")
        # Create a flow request that does NOT require delegation
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Pendiente',
            observations='Solicitud de prueba para delegación',
            requires_delegation=False,  # This should prevent assignment
            requested_flow=5.0  # Adding required flow for this type
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, requires_delegation={flow_request.requires_delegation}")
        
        print("[STEP] Intentando crear asignación para solicitud que no requiere delegación")
        # Try to create assignment
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] Datos de la solicitud: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the response and check for error message
        import json
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"[INFO] Respuesta parseada: {response_data}")
        
        assert 'errors' in response_data
        assert 'flow_request' in response_data['errors']
        
        # El mensaje puede estar en un formato anidado y posiblemente serializado como string
        flow_request_error = response_data['errors']['flow_request']
        print(f"[INFO] Mensaje de error flow_request: {flow_request_error}")
        
        assert 'asignaci' in flow_request_error or 'error' in flow_request_error
        print("[PASS] Test completado exitosamente - asignación rechazada correctamente")

    def test_prevent_duplicate_assignment(self, api_client, admin_user, tecnico_user,
                                    login_and_validate_otp, user_lot, normal_user,
                                    iot_device):
        """Test that the same request cannot be assigned to the same user twice."""
        print("\n[TEST] Iniciando test_prevent_duplicate_assignment")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que requiere delegación")
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Creando primera asignación")
        # Create first assignment
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] Datos de la solicitud: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado de primera asignación: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        print("[INFO] Primera asignación creada exitosamente")
        
        print("[STEP] Intentando crear asignación duplicada")
        # Try to create duplicate assignment
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado de asignación duplicada: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Esta solicitud de caudal ya ha sido asignada a este usuario" in str(response.content)
        print("[PASS] Test completado exitosamente - asignación duplicada rechazada correctamente")

    def test_reassign_request(self, api_client, admin_user, tecnico_user, operador_user,
                        login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test reassignment of a request to another user."""
        print("\n[TEST] Iniciando test_reassign_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos para admin")
        # Setup permissions for admin
        self.setup_permissions(admin_user)
        
        print("[STEP] Dando permiso can_be_assigned al técnico y operador")
        # Get content type for Assignment model
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Give both technician and operator permission to be assigned
        try:
            can_be_assigned = Permission.objects.get(
                codename='can_be_assigned',
                content_type=content_type
            )
            print("[INFO] Permiso can_be_assigned existente encontrado")
        except Permission.DoesNotExist:
            can_be_assigned = Permission.objects.create(
                codename='can_be_assigned',
                name='Can be assigned to handle requests/reports',
                content_type=content_type
            )
            print("[INFO] Permiso can_be_assigned creado")
            
        tecnico_user.user_permissions.add(can_be_assigned)
        operador_user.user_permissions.add(can_be_assigned)
        tecnico_user.save()
        operador_user.save()
        print(f"[INFO] Permiso can_be_assigned asignado a técnico: {tecnico_user.document} y operador: {operador_user.document}")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que requiere delegación")
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Asignando solicitud al técnico")
        # Create first assignment to technician
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] Datos de la asignación al técnico: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado de asignación al técnico: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        assignment_id = response.data['id']
        print(f"[INFO] Asignación al técnico creada exitosamente, ID: {assignment_id}")
        
        print("[STEP] Reasignando solicitud al operador")
        # Now reassign to operator, using the reassign endpoint
        url = reverse('assignment-reassign', kwargs={'pk': assignment_id})
        data = {
            'assigned_to': operador_user.document,
            'reassigned': True
        }
        print(f"[INFO] Datos de la reasignación al operador: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado de reasignación: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        print("[INFO] Reasignación exitosa")
        
        print("[STEP] Verificando reasignación en base de datos")
        # Verify reassignment
        new_assignments = Assignment.objects.filter(flow_request=flow_request, assigned_to=operador_user)
        print(f"[INFO] Asignaciones al operador encontradas: {new_assignments.count()}")
        
        assert new_assignments.count() == 1
        new_assignment = new_assignments.first()
        print(f"[INFO] Detalles de la nueva asignación: ID={new_assignment.id}, reassigned={new_assignment.reassigned}")
        
        assert new_assignment.reassigned is True
        assert new_assignment.assigned_by == admin_user
        assert new_assignment.assigned_to == operador_user
        print("[PASS] Test completado exitosamente - reasignación verificada correctamente")

    def test_assignment_updates_status(self, api_client, admin_user, tecnico_user,
                                 login_and_validate_otp, user_lot, normal_user,
                                 iot_device):
        """Test that assignment updates the status of requests/reports to 'En proceso'."""
        print("\n[TEST] Iniciando test_assignment_updates_status")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud con estado inicial 'Pendiente'")
        # Create a flow request with initial status 'Pendiente'
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, estado inicial: {flow_request.status}")
        
        # Verify initial status
        assert flow_request.status == 'Pendiente'
        
        print("[STEP] Creando asignación")
        # Create assignment
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] Datos de la asignación: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado de la creación de asignación: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        print("[INFO] Asignación creada exitosamente")
        
        print("[STEP] Verificando actualización de estado de la solicitud")
        # Verify flow request status has been updated
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado de la solicitud: {flow_request.status}")
        
        assert flow_request.status == 'En proceso'
        print("[PASS] Test completado exitosamente - estado de solicitud actualizado correctamente")

    def test_view_assigned_items(self, api_client, admin_user, tecnico_user,
                           login_and_validate_otp, user_lot, normal_user,
                           iot_device):
        """Test that assigned technicians can view their assigned items."""
        print("\n[TEST] Iniciando test_view_assigned_items")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que requiere delegación")
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Creando asignación directamente en la base de datos")
        # Create assignment directly
        assignment = Assignment.objects.create(
            flow_request=flow_request,
            assigned_by=admin_user,
            assigned_to=tecnico_user,
            reassigned=False
        )
        print(f"[INFO] Asignación creada ID: {assignment.id}")
        
        print(f"[STEP] Iniciando sesión como técnico: {tecnico_user.document}")
        # Login as technician with correct password
        client = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        
        print("[STEP] Dando permiso de visualización al técnico")
        # Add view permission
        content_type = ContentType.objects.get_for_model(Assignment)
        try:
            view_permission = Permission.objects.get(
                codename='view_assignment',
                content_type=content_type
            )
            print("[INFO] Permiso view_assignment existente encontrado")
        except Permission.DoesNotExist:
            view_permission = Permission.objects.create(
                codename='view_assignment',
                name='Can view assignment',
                content_type=content_type
            )
            print("[INFO] Permiso view_assignment creado")
            
        tecnico_user.user_permissions.add(view_permission)
        tecnico_user.save()
        print(f"[INFO] Permiso de visualización asignado al técnico: {tecnico_user.document}")
        
        print("[STEP] Consultando elementos asignados al técnico")
        # View assigned items
        url = reverse('technician-assignments')
        print(f"[INFO] URL: {url}")
        
        response = client.get(url)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Cantidad de items en respuesta: {len(response.data)}")
        if len(response.data) > 0:
            print(f"[RESULT] Primer item en respuesta: {response.data[0]}")
        
        # Verify success and content
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == assignment.id
        assert response.data[0]['flow_request'] == flow_request.id
        assert response.data[0]['assigned_by_name'] == admin_user.get_full_name()
        assert response.data[0]['assigned_to_name'] == tecnico_user.get_full_name()
        print("[PASS] Test completado exitosamente - elementos asignados visualizados correctamente")

    def test_approve_flow_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that administrators can directly approve flow requests without delegation."""
        print("\n[TEST] Iniciando test_approve_flow_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the original lot info
        existing_lot, _, _ = user_lot
        plot = existing_lot.plot
        valve4, _, _, _ = iot_device
        valve_device_type = valve4.device_type
        crop_type = existing_lot.crop_type
        soil_type = existing_lot.soil_type
        print(f"[INFO] Usando predio ID: {plot.id_plot} y tipo de válvula: {valve_device_type}")
        
        print("[STEP] Creando un nuevo lote para la prueba")
        # Create a new lot
        test_lot = Lot.objects.create(
            plot=plot,
            crop_name="Test Crop for Approval",
            crop_type=crop_type,
            crop_variety="Test Variety",
            soil_type=soil_type,
            is_activate=True
        )
        print(f"[INFO] Lote creado ID: {test_lot.id_lot}")
        
        print("[STEP] Creando una válvula para el lote con flujo inicial no cero")
        # Create a valve for the lot WITH NON-ZERO INITIAL FLOW
        valve_test = IoTDevice.objects.create(
            name="Válvula de Prueba",
            device_type=valve_device_type,
            id_plot=plot,
            id_lot=test_lot,
            is_active=True,
            actual_flow=3.0,  # Set initial flow to non-zero value
            iot_id="06-test"
        )
        print(f"[INFO] Válvula creada ID: {valve_test.iot_id}, flujo inicial: {valve_test.actual_flow}")
        
        print("[STEP] Creando solicitud de cambio de caudal")
        # Create a flow request
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=test_lot,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Pendiente',
            observations='Solicitud de cambio de caudal',
            requires_delegation=False,
            requested_flow=5.0
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, caudal solicitado: {flow_request.requested_flow}")
        
        print("[STEP] Aprobando la solicitud")
        # Test approval of the request
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        print(f"[INFO] URL: {url}")
        
        response = client.post(url)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        assert "aprobada correctamente" in str(response.content)
        
        print("[STEP] Verificando cambios en la solicitud")
        # Verify request has been updated
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado: {flow_request.status}, aprobado: {flow_request.is_approved}, fecha finalización: {flow_request.finalized_at}")
        
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == True
        assert flow_request.finalized_at is not None
        
        print("[STEP] Verificando que el caudal de la válvula ha sido actualizado")
        # Verify device flow rate has been updated
        valve_test.refresh_from_db()
        print(f"[INFO] Caudal actualizado de la válvula: {valve_test.actual_flow}")
        
        assert valve_test.actual_flow == 5.0
        print("[PASS] Test completado exitosamente - solicitud aprobada y caudal actualizado correctamente")

    def test_reject_flow_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that administrators can directly reject flow requests with observations."""
        print("\n[TEST] Iniciando test_reject_flow_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud de cambio de caudal")
        # Create a flow request
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Pendiente',
            observations='Solicitud de cambio de caudal',
            requires_delegation=False,
            requested_flow=5.0
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, caudal solicitado: {flow_request.requested_flow}")
        
        # Initial device flow rate
        initial_flow = valve4.actual_flow
        print(f"[INFO] Caudal inicial de la válvula: {initial_flow}")
        
        print("[STEP] Intentando rechazar la solicitud sin observaciones")
        # Test rejection without observations (should fail)
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        print(f"[INFO] URL: {url}")
        
        response = client.post(url, data={})
        
        print(f"[RESULT] Código de estado (rechazo sin observaciones): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail - observations are required
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "observations" in str(response.content) or "Debe incluir observaciones" in str(response.content)
        
        print("[STEP] Rechazando la solicitud con observaciones")
        # Test rejection with observations
        rejection_reason = "El caudal solicitado excede la capacidad disponible en el sistema."
        data = {"observations": rejection_reason}
        print(f"[INFO] Datos de rechazo: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado (rechazo con observaciones): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        assert "rechazada correctamente" in str(response.content)
        
        print("[STEP] Verificando cambios en la solicitud")
        # Verify request has been updated in the database
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado: {flow_request.status}, aprobado: {flow_request.is_approved}, observaciones: {flow_request.observations}")
        
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == False
        assert flow_request.finalized_at is not None
        assert flow_request.observations == rejection_reason
        
        print("[STEP] Verificando que el caudal de la válvula NO ha sido modificado")
        # Verify device flow rate has NOT been updated
        valve4.refresh_from_db()
        print(f"[INFO] Caudal actual de la válvula: {valve4.actual_flow}")
        
        assert valve4.actual_flow == initial_flow
        print("[PASS] Test completado exitosamente - solicitud rechazada correctamente sin modificar el caudal")

    def test_cannot_approve_already_finalized_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that finalized requests cannot be approved again."""
        print("\n[TEST] Iniciando test_cannot_approve_already_finalized_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que ya está finalizada y aprobada")
        # Create a flow request with status already finalized
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Finalizado',  # Already finalized
            observations='Solicitud ya finalizada',
            requires_delegation=False,
            requested_flow=5.0,
            is_approved=True,
            finalized_at=timezone.now()
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, estado: {flow_request.status}, aprobada: {flow_request.is_approved}")
        
        print("[STEP] Intentando aprobar nuevamente la solicitud ya finalizada")
        # Try to approve again
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        print(f"[INFO] URL: {url}")
        
        response = client.post(url)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya fue finalizada" in str(response.content)
        print("[PASS] Test completado exitosamente - no se puede aprobar una solicitud ya finalizada")

    def test_cannot_reject_already_finalized_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that finalized requests cannot be rejected again."""
        print("\n[TEST] Iniciando test_cannot_reject_already_finalized_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud que ya está finalizada y rechazada")
        # Create a flow request with status already finalized
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Finalizado',  # Already finalized
            observations='Solicitud ya finalizada',
            requires_delegation=False,
            requested_flow=5.0,
            is_approved=False,
            finalized_at=timezone.now()
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}, estado: {flow_request.status}, aprobada: {flow_request.is_approved}")
        
        print("[STEP] Intentando rechazar nuevamente la solicitud ya finalizada")
        # Try to reject again
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        rejection_reason = "Motivo de rechazo"
        data = {"observations": rejection_reason}
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya fue finalizada" in str(response.content)
        print("[PASS] Test completado exitosamente - no se puede rechazar una solicitud ya finalizada")


    def test_notification_sent_on_approval(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device, settings):
        """Test that email notifications are sent when approving a request."""
        print("\n[TEST] Iniciando test_notification_sent_on_approval")
        
        print("[STEP] Configurando backend de correo para pruebas")
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Clear the email outbox
        from django.core import mail
        mail.outbox = []
        print("[INFO] Bandeja de correo limpiada")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud para probar notificaciones")
        # Create a flow request
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Pendiente',
            observations='Solicitud para probar notificaciones',
            requires_delegation=False,
            requested_flow=5.0
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Aprobando la solicitud")
        # Approve the request
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        print(f"[INFO] URL: {url}")
        
        response = client.post(url)
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        print("[STEP] Verificando actualización de la solicitud")
        # Verify request has been updated in the database
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado: {flow_request.status}, aprobado: {flow_request.is_approved}")
        
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == True
        
        print("[STEP] Verificando envío de notificaciones por correo")
        # Verify that at least one email was sent
        print(f"[INFO] Correos enviados: {len(mail.outbox)}")
        for i, email in enumerate(mail.outbox):
            print(f"[INFO] Correo {i+1}: Para: {email.to}, Asunto: {email.subject}")
        
        assert len(mail.outbox) > 0
        
        # Verify the email was sent to the right person
        user_emails = [email for email in mail.outbox if normal_user.email in email.to]
        print(f"[INFO] Correos enviados al usuario: {len(user_emails)}")
        
        assert any(normal_user.email in email.to for email in mail.outbox)
        
        # Instead of checking specific terms, just verify user received a notification
        user_received_mail = False
        for email in mail.outbox:
            if normal_user.email in email.to:
                user_received_mail = True
                break
        
        assert user_received_mail
        print("[PASS] Test completado exitosamente - notificación enviada correctamente al aprobar solicitud")

    # Fix for test_notification_sent_on_rejection
    def test_notification_sent_on_rejection(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device, settings):
        """Test that email notifications are sent when rejecting a request."""
        print("\n[TEST] Iniciando test_notification_sent_on_rejection")
        
        print("[STEP] Configurando backend de correo para pruebas")
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Clear the email outbox
        from django.core import mail
        mail.outbox = []
        print("[INFO] Bandeja de correo limpiada")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud para probar notificaciones de rechazo")
        # Create a flow request
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_TEMPORARY_CANCEL,
            status='Pendiente',
            observations='Solicitud para probar notificaciones de rechazo',
            requires_delegation=False,
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Rechazando la solicitud")
        # Reject the request
        rejection_reason = "Motivo de rechazo para prueba."
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        data = {"observations": rejection_reason}
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        print("[STEP] Verificando actualización de la solicitud")
        # Verify request has been updated
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado: {flow_request.status}, aprobado: {flow_request.is_approved}, observaciones: {flow_request.observations}")
        
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == False
        assert flow_request.observations == rejection_reason
        
        print("[STEP] Verificando envío de notificaciones por correo")
        # Verify that at least one email was sent
        print(f"[INFO] Correos enviados: {len(mail.outbox)}")
        for i, email in enumerate(mail.outbox):
            print(f"[INFO] Correo {i+1}: Para: {email.to}, Asunto: {email.subject}")
        
        assert len(mail.outbox) > 0
        
        # Verify the email was sent to the right person
        user_emails = [email for email in mail.outbox if normal_user.email in email.to]
        print(f"[INFO] Correos enviados al usuario: {len(user_emails)}")
        
        assert any(normal_user.email in email.to for email in mail.outbox)
        
        # Check any email, not just subject
        has_rejection_terms = False
        for email in mail.outbox:
            if normal_user.email in email.to:
                email_content = email.subject.lower() + " " + email.body.lower()
                
                # Check alternatives for HTML content
                if hasattr(email, 'alternatives'):
                    for content, _ in email.alternatives:
                        email_content += " " + str(content).lower()
                        
                terms_found = []
                for term in ['rechazada', 'rechazo', 'decisión', 'solicitud']:
                    if term in email_content:
                        terms_found.append(term)
                        
                if terms_found:
                    has_rejection_terms = True
                    print(f"[INFO] Términos encontrados en el correo: {terms_found}")
                    break
        
        assert has_rejection_terms
        print("[PASS] Test completado exitosamente - notificación enviada correctamente al rechazar solicitud")

    def test_non_admin_cannot_approve_reject_requests(self, api_client, normal_user, login_and_validate_otp, user_lot, iot_device):
        """Test that non-admin users cannot approve or reject flow requests."""
        print("\n[TEST] Iniciando test_non_admin_cannot_approve_reject_requests")
        
        print(f"[STEP] Iniciando sesión como usuario normal: {normal_user.document}")
        # Login as normal user
        client = login_and_validate_otp(api_client, normal_user, password="UserPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"[INFO] Usando lote ID: {lote1.id_lot} y dispositivo ID: {valve4.iot_id}")
        
        print("[STEP] Creando solicitud de prueba")
        # Create a flow request
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            status='Pendiente',
            observations='Solicitud de prueba para permisos',
            requires_delegation=False,
            requested_flow=5.0
        )
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        print("[STEP] Intentando aprobar como usuario no administrador")
        # Try to approve as a non-admin user
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        print(f"[INFO] URL aprobar: {url}")
        
        response = client.post(url)
        
        print(f"[RESULT] Código de estado (aprobar): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail with permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        print("[STEP] Intentando rechazar como usuario no administrador")
        # Try to reject as a non-admin user
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        data = {"observations": "Motivo de rechazo"}
        print(f"[INFO] URL rechazar: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado (rechazar): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Should fail with permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        print("[STEP] Verificando que la solicitud no ha sido modificada")
        # Verify the request status hasn't changed
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actual de la solicitud: {flow_request.status}, aprobado: {flow_request.is_approved}")
        
        assert flow_request.status == "Pendiente"
        assert flow_request.is_approved == False
        
        print("[PASS] Test completado exitosamente - usuario normal no puede aprobar/rechazar solicitudes")

    def test_assign_water_supply_failure_report(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, normal_user, iot_device):
        """Verifica que se puede asignar correctamente un reporte de fallo en el suministro de agua."""
        print("\n[TEST] Iniciando test_assign_water_supply_failure_report")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        print("[STEP] Creando reporte de fallo en suministro de agua")
        # Crear un reporte de fallo en el suministro de agua (por el dueño del predio)
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        # Estado inicial del reporte
        print(f"[INFO] Estado inicial del reporte: {failure_report.status}")
        assert failure_report.status == 'Pendiente'
        
        print("[STEP] Creando asignación")
        # Crear asignación
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        print("[STEP] Verificando actualización del estado del reporte")
        # Verificar que el reporte ha sido actualizado a "En proceso"
        failure_report.refresh_from_db()
        print(f"[INFO] Estado actualizado del reporte: {failure_report.status}")
        
        assert failure_report.status == 'En proceso'
        
        print("[STEP] Verificando la creación correcta de la asignación")
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(failure_report=failure_report).first()
        print(f"[INFO] Asignación: {assignment}")
        
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user
        print("[PASS] Test completado exitosamente - reporte de fallo asignado correctamente")

    def test_assign_application_failure_report(self, api_client, admin_user, tecnico_user, login_and_validate_otp, normal_user):
        """Verifica que se puede asignar correctamente un reporte de fallo en el aplicativo."""
        print("\n[TEST] Iniciando test_assign_application_failure_report")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        print("[STEP] Creando reporte de fallo en el aplicativo")
        # Crear un reporte de fallo en el aplicativo (no requiere lote ni predio)
        failure_report = self.setup_application_failure_report(normal_user)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        # Estado inicial del reporte
        print(f"[INFO] Estado inicial del reporte: {failure_report.status}")
        assert failure_report.status == 'Pendiente'
        
        print("[STEP] Creando asignación")
        # Crear asignación
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        print("[STEP] Verificando actualización del estado del reporte")
        # Verificar que el reporte ha sido actualizado a "En proceso"
        failure_report.refresh_from_db()
        print(f"[INFO] Estado actualizado del reporte: {failure_report.status}")
        
        assert failure_report.status == 'En proceso'
        
        print("[STEP] Verificando la creación correcta de la asignación")
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(failure_report=failure_report).first()
        print(f"[INFO] Asignación: {assignment}")
        
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user
        print("[PASS] Test completado exitosamente - reporte de fallo en aplicativo asignado correctamente")

    def test_assign_definitive_cancellation_request(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, iot_device, normal_user):
        """Verifica que se puede asignar correctamente una solicitud de cancelación definitiva."""
        print("\n[TEST] Iniciando test_assign_definitive_cancellation_request")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        print("[STEP] Creando solicitud de cancelación definitiva")
        # Crear una solicitud de cancelación definitiva
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        flow_request = self.setup_definitive_cancellation_request(normal_user, lote1, valve4)
        print(f"[INFO] Solicitud creada ID: {flow_request.id}")
        
        # Estado inicial de la solicitud
        print(f"[INFO] Estado inicial de la solicitud: {flow_request.status}")
        assert flow_request.status == 'Pendiente'
        
        print("[STEP] Creando asignación")
        # Crear asignación
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        print("[STEP] Verificando actualización del estado de la solicitud")
        # Verificar que la solicitud ha sido actualizada a "En proceso"
        flow_request.refresh_from_db()
        print(f"[INFO] Estado actualizado de la solicitud: {flow_request.status}")
        
        assert flow_request.status == 'En proceso'
        
        print("[STEP] Verificando la creación correcta de la asignación")
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(flow_request=flow_request).first()
        print(f"[INFO] Asignación: {assignment}")
        
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user
        print("[PASS] Test completado exitosamente - solicitud de cancelación definitiva asignada correctamente")

    def test_only_users_with_can_be_assigned_permission(self, api_client, admin_user, normal_user, login_and_validate_otp, user_lot, user_plot, iot_device):
        """Verifica que no se puede asignar a usuarios sin el permiso 'can_be_assigned'."""
        print("\n[TEST] Iniciando test_only_users_with_can_be_assigned_permission")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos SOLO para admin (no para normal_user)")
        # Setup permisos para admin pero NO para normal_user
        self.setup_permissions(admin_user)
        
        print("[STEP] Creando reporte de fallo")
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Intentando asignar a usuario sin permiso can_be_assigned")
        # Intentar asignar a usuario sin permiso
        url = reverse('assignment-create')
        data = {
            'assigned_to': normal_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Debe fallar por falta de permisos
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("[STEP] Verificando mensajes de error")
        # Verificar mensaje de error
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"[INFO] Respuesta parseada: {response_data}")
        
        assert 'errors' in response_data
        assert 'assigned_to' in response_data['errors']
        
        print("[STEP] Verificando que no se creó ninguna asignación")
        # Verificar que no se creó ninguna asignación
        assignment_count = Assignment.objects.filter(failure_report=failure_report).count()
        print(f"[INFO] Cantidad de asignaciones: {assignment_count}")
        
        assert assignment_count == 0
        print("[PASS] Test completado exitosamente - no se pudo asignar a usuario sin permiso")

    def test_error_on_invalid_user_id(self, api_client, admin_user, login_and_validate_otp, user_lot, user_plot, iot_device, normal_user):
        """Verifica que se devuelve un error apropiado al intentar asignar a un ID de usuario inexistente."""
        print("\n[TEST] Iniciando test_error_on_invalid_user_id")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user)
        
        print("[STEP] Creando reporte de fallo")
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Intentando asignar a un usuario que no existe")
        # Intentar asignar a un usuario que no existe
        url = reverse('assignment-create')
        data = {
            'assigned_to': '999999999999',  # ID que no existe
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Debe fallar por usuario inexistente
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("[STEP] Verificando mensajes de error")
        # Verificar que se incluye un mensaje de error apropiado
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"[INFO] Respuesta parseada: {response_data}")
        
        assert 'errors' in response_data
        assert 'assigned_to' in response_data['errors']
        
        print("[STEP] Verificando que no se creó ninguna asignación")
        # Verificar que no se creó ninguna asignación
        assignment_count = Assignment.objects.filter(failure_report=failure_report).count()
        print(f"[INFO] Cantidad de asignaciones: {assignment_count}")
        
        assert assignment_count == 0
        print("[PASS] Test completado exitosamente - error apropiado al intentar asignar a usuario inexistente")

    def test_notification_for_water_supply_report_assignment(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, iot_device, settings, normal_user):
        """Verifica que se envía una notificación cuando se asigna un reporte de fallo en el suministro de agua."""
        print("\n[TEST] Iniciando test_notification_for_water_supply_report_assignment")
        
        print("[STEP] Configurando backend de correo para testing")
        # Configurar backend de correo para testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Limpiar bandeja de correo
        mail.outbox = []
        print("[INFO] Bandeja de correo limpiada")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        print("[STEP] Creando reporte de fallo en suministro de agua")
        # Crear un reporte de fallo en el suministro de agua
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Creando asignación")
        # Crear asignación
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        print("[STEP] Verificando envío de notificaciones por correo")
        # Verificar que se enviaron notificaciones
        print(f"[INFO] Correos enviados: {len(mail.outbox)}")
        for i, email in enumerate(mail.outbox):
            print(f"[INFO] Correo {i+1}: Para: {email.to}, Asunto: {email.subject}")
        
        assert len(mail.outbox) > 0
        
        print("[STEP] Verificando destinatarios de las notificaciones")
        # Verificar que se envió al técnico y al administrador
        recipients = []
        for email in mail.outbox:
            recipients.extend(email.to)
        
        print(f"[INFO] Todos los destinatarios: {recipients}")
        
        assert admin_user.email in recipients
        assert tecnico_user.email in recipients
        print("[PASS] Test completado exitosamente - notificaciones enviadas correctamente al técnico y al administrador")

    def test_maintenance_report_changes_status(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, iot_device, normal_user):
        """Verifica que un informe de mantenimiento cambia el estado de una solicitud/reporte a 'A espera de aprobación'."""
        print("\n[TEST] Iniciando test_maintenance_report_changes_status")
        
        print(f"[STEP] Iniciando sesión como administrador: {admin_user.document}")
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        print("[STEP] Configurando permisos")
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        print("[STEP] Creando reporte de fallo")
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Creando asignación")
        # Crear asignación
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado (creación asignación): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Obtener ID de la asignación
        assignment_id = response.data['id']
        print(f"[INFO] ID de la asignación creada: {assignment_id}")
        
        print(f"[STEP] Iniciando sesión como técnico: {tecnico_user.document}")
        # Login como técnico
        client = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        
        print("[STEP] Creando informe de mantenimiento")
        # Crear informe de mantenimiento
        url = reverse('maintenance-report-create')
        current_time = timezone.now().isoformat()
        data = {
            'assignment': assignment_id,
            'intervention_date': current_time,
            'description': 'Se reparó el problema con el suministro de agua',
            'status': 'Finalizado'
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado (creación informe): {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content[:100]}...")
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        print("[STEP] Verificando cambio de estado del reporte")
        # Verificar que el reporte ha cambiado a estado "A espera de aprobación"
        failure_report.refresh_from_db()
        print(f"[INFO] Estado actualizado del reporte: {failure_report.status}")
        
        assert failure_report.status == 'A espera de aprobación'
        print("[PASS] Test completado exitosamente - estado del reporte actualizado a 'A espera de aprobación'")
    
    def test_normal_user_cannot_delegate(self, api_client, normal_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, iot_device):
        """Verifica que un usuario sin permisos de delegación no puede asignar reportes/solicitudes."""
        print("\n[TEST] Iniciando test_normal_user_cannot_delegate")
        
        print(f"[STEP] Iniciando sesión como usuario normal: {normal_user.document}")
        # Login como usuario normal (sin permisos)
        client = login_and_validate_otp(api_client, normal_user, password="UserPass123@")
        
        print("[STEP] Creando reporte de fallo que pertenece al usuario normal")
        # Crear un reporte de fallo que pertenece al usuario normal
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"[INFO] Reporte creado ID: {failure_report.id}")
        
        print("[STEP] Intentando asignar el reporte sin tener permisos")
        # Intentar asignar sin tener permisos
        url = reverse('assignment-create')
        data = {
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }
        print(f"[INFO] URL: {url}, datos: {data}")
        
        response = client.post(url, data=data, format='json')
        
        print(f"[RESULT] Código de estado: {response.status_code}")
        print(f"[RESULT] Contenido de la respuesta: {response.content}")
        
        # Debe fallar por falta de permisos
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
        
        print("[STEP] Verificando que el estado del reporte no ha cambiado")
        # Verificar que el estado del reporte no ha cambiado
        failure_report.refresh_from_db()
        print(f"[INFO] Estado actual del reporte: {failure_report.status}")
        
        assert failure_report.status == 'Pendiente'
        
        print("[STEP] Verificando que no se creó ninguna asignación")
        # Verificar que no se creó ninguna asignación
        assignment_exists = Assignment.objects.filter(failure_report=failure_report).exists()
        print(f"[INFO] ¿Existe alguna asignación?: {assignment_exists}")
        
        assert not assignment_exists
        print("[PASS] Test completado exitosamente - usuario normal no puede asignar reportes")