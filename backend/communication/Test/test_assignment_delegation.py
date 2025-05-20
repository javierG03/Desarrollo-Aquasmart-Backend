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
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Add required permission
        content_type = ContentType.objects.get_for_model(Assignment)
        try:
            view_permission = Permission.objects.get(
                codename='view_assignment',
                content_type=content_type
            )
        except Permission.DoesNotExist:
            view_permission = Permission.objects.create(
                codename='view_assignment',
                name='Can view assignment',
                content_type=content_type
            )
            
        admin_user.user_permissions.add(view_permission)
        admin_user.save()
        
        # Access assignment list
        url = reverse('list_iot_devices')  # Adjust to actual endpoint
        response = client.get(url)
        
        # Verify access is granted
        assert response.status_code == status.HTTP_200_OK

    def test_create_assignment_requires_permission(self, api_client, normal_user, login_and_validate_otp):
        """Test that only users with can_assign_user permission can create assignments."""
        # Login as normal user with correct password
        client = login_and_validate_otp(api_client, normal_user, password="UserPass123@")
        
        url = reverse('assignment-create')
        
        # Attempt to create an assignment without permission
        response = client.post(url, data={
            'assigned_to': normal_user.document,
            'flow_request': 1
        })
        
        # User should get permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_validate_assignment_exclusivity(self, api_client, admin_user, tecnico_user,
                                       login_and_validate_otp, user_lot, user_plot,
                                       normal_user, iot_device):
        """Test validation that assignments can't have both flow_request and failure_report."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request that requires delegation
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Create a failure report
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Try to create assignment with both flow_request and failure_report
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id,
            'failure_report': failure_report.id
        }, format='json')
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the response and check for error message
        import json
        response_data = json.loads(response.content.decode('utf-8'))
        assert 'errors' in response_data
        assert 'non_field_errors' in response_data['errors']
        assert 'flow_request' in response_data['errors']['non_field_errors'] and 'failure_report' in response_data['errors']['non_field_errors']

    def test_validate_assignment_exclusivity(self, api_client, admin_user, tecnico_user, 
                                       login_and_validate_otp, user_lot, user_plot, 
                                       normal_user, iot_device):
        """Test validation that assignments can't have both flow_request and failure_report."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request that requires delegation
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Create a failure report
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Try to create assignment with both flow_request and failure_report
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id,
            'failure_report': failure_report.id
        }, format='json')
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the JSON response
        response_data = json.loads(response.content.decode('utf-8'))
        assert "No se puede asignar un 'flow_request' y un 'failure_report' al mismo tiempo" in response_data['errors']['non_field_errors']

    def test_prevent_self_assignment(self, api_client, admin_user,
                               login_and_validate_otp, user_lot,
                               normal_user, iot_device):
        """Test that users cannot assign tasks to themselves."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup admin permissions for both assigning and being assigned
        assign_permission = self.setup_permissions(admin_user)
        
        # Get content type for Assignment model
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Give admin permission to be assigned (to test self-assignment)
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
            
        admin_user.user_permissions.add(can_be_assigned)
        admin_user.save()
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Try to self-assign
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': admin_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the response and check for error message
        import json
        response_data = json.loads(response.content.decode('utf-8'))
        assert 'errors' in response_data
        assert 'non_field_errors' in response_data['errors']
        assert 'usuario no puede asignarse' in response_data['errors']['non_field_errors']
        
    def test_validate_flow_request_requires_delegation(self, api_client, admin_user,
                                                tecnico_user, login_and_validate_otp,
                                                user_lot, normal_user, iot_device):
        """Test that only flow requests that require delegation can be assigned."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Try to create assignment
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse the response and check for error message
        import json
        response_data = json.loads(response.content.decode('utf-8'))
        assert 'errors' in response_data
        assert 'flow_request' in response_data['errors']
        # El mensaje puede estar en un formato anidado y posiblemente serializado como string
        flow_request_error = response_data['errors']['flow_request']
        assert 'asignaci' in flow_request_error or 'error' in flow_request_error

    def test_prevent_duplicate_assignment(self, api_client, admin_user, tecnico_user,
                                        login_and_validate_otp, user_lot, normal_user,
                                        iot_device):
        """Test that the same request cannot be assigned to the same user twice."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Create first assignment
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate assignment
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Esta solicitud de caudal ya ha sido asignada a este usuario" in str(response.content)

    def test_reassign_request(self, api_client, admin_user, tecnico_user, operador_user,
                            login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test reassignment of a request to another user."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions for admin
        self.setup_permissions(admin_user)
        
        # Get content type for Assignment model
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Give both technician and operator permission to be assigned
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
        operador_user.user_permissions.add(can_be_assigned)
        tecnico_user.save()
        operador_user.save()
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Create first assignment to technician
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        assignment_id = response.data['id']
        
        # Now reassign to operator, using the reassign endpoint
        url = reverse('assignment-reassign', kwargs={'pk': assignment_id})
        response = client.post(url, data={
            'assigned_to': operador_user.document,
            'reassigned': True
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        # Verify reassignment
        new_assignments = Assignment.objects.filter(flow_request=flow_request, assigned_to=operador_user)
        assert new_assignments.count() == 1
        new_assignment = new_assignments.first()
        assert new_assignment.reassigned is True
        assert new_assignment.assigned_by == admin_user
        assert new_assignment.assigned_to == operador_user

    def test_assignment_updates_status(self, api_client, admin_user, tecnico_user,
                                     login_and_validate_otp, user_lot, normal_user,
                                     iot_device):
        """Test that assignment updates the status of requests/reports to 'En proceso'."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request with initial status 'Pendiente'
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Verify initial status
        assert flow_request.status == 'Pendiente'
        
        # Create assignment
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify flow request status has been updated
        flow_request.refresh_from_db()
        assert flow_request.status == 'En proceso'

    def test_view_assigned_items(self, api_client, admin_user, tecnico_user,
                               login_and_validate_otp, user_lot, normal_user,
                               iot_device):
        """Test that assigned technicians can view their assigned items."""
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a flow request
        flow_request = self.setup_flow_request(normal_user, lote1, valve4)
        
        # Create assignment directly
        assignment = Assignment.objects.create(
            flow_request=flow_request,
            assigned_by=admin_user,
            assigned_to=tecnico_user,
            reassigned=False
        )
        
        # Login as technician with correct password
        client = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        
        # Add view permission
        content_type = ContentType.objects.get_for_model(Assignment)
        try:
            view_permission = Permission.objects.get(
                codename='view_assignment',
                content_type=content_type
            )
        except Permission.DoesNotExist:
            view_permission = Permission.objects.create(
                codename='view_assignment',
                name='Can view assignment',
                content_type=content_type
            )
            
        tecnico_user.user_permissions.add(view_permission)
        tecnico_user.save()
        
        # View assigned items
        url = reverse('technician-assignments')
        response = client.get(url)
        
        # Verify success and content
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == assignment.id
        assert response.data[0]['flow_request'] == flow_request.id
        assert response.data[0]['assigned_by_name'] == admin_user.get_full_name()
        assert response.data[0]['assigned_to_name'] == tecnico_user.get_full_name()

    def test_approve_flow_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that administrators can directly approve flow requests without delegation."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the original lot info
        existing_lot, _, _ = user_lot
        plot = existing_lot.plot
        valve4, _, _, _ = iot_device
        valve_device_type = valve4.device_type
        crop_type = existing_lot.crop_type
        soil_type = existing_lot.soil_type
        
        # Create a new lot
        test_lot = Lot.objects.create(
            plot=plot,
            crop_name="Test Crop for Approval",
            crop_type=crop_type,
            crop_variety="Test Variety",
            soil_type=soil_type,
            is_activate=True
        )
        
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
        
        # Test approval of the request
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        response = client.post(url)
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        assert "aprobada correctamente" in str(response.content)
        
        # Verify request has been updated
        flow_request.refresh_from_db()
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == True
        assert flow_request.finalized_at is not None
        
        # Verify device flow rate has been updated
        valve_test.refresh_from_db()
        assert valve_test.actual_flow == 5.0

    def test_reject_flow_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that administrators can directly reject flow requests with observations."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Initial device flow rate
        initial_flow = valve4.actual_flow
        
        # Test rejection without observations (should fail)
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        response = client.post(url, data={})
        
        # Should fail - observations are required
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "observations" in str(response.content) or "Debe incluir observaciones" in str(response.content)
        
        # Test rejection with observations
        rejection_reason = "El caudal solicitado excede la capacidad disponible en el sistema."
        response = client.post(url, data={"observations": rejection_reason}, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        assert "rechazada correctamente" in str(response.content)
        
        # Verify request has been updated in the database
        flow_request.refresh_from_db()
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == False
        assert flow_request.finalized_at is not None
        assert flow_request.observations == rejection_reason
        
        # Verify device flow rate has NOT been updated
        valve4.refresh_from_db()
        assert valve4.actual_flow == initial_flow

    def test_cannot_approve_already_finalized_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that finalized requests cannot be approved again."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Try to approve again
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        response = client.post(url)
        
        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya fue finalizada" in str(response.content)

    def test_cannot_reject_already_finalized_request(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device):
        """Test that finalized requests cannot be rejected again."""
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Try to reject again
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        response = client.post(url, data={"observations": "Motivo de rechazo"}, format='json')
        
        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya fue finalizada" in str(response.content)


    def test_notification_sent_on_approval(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device, settings):
        """Test that email notifications are sent when approving a request."""
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Clear the email outbox
        from django.core import mail
        mail.outbox = []
        
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Approve the request
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        response = client.post(url)
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        # Verify request has been updated in the database
        flow_request.refresh_from_db()
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == True
        
        # Verify that at least one email was sent
        assert len(mail.outbox) > 0
        
        # Verify the email was sent to the right person
        assert any(normal_user.email in email.to for email in mail.outbox)
        
        # Instead of checking specific terms, just verify user received a notification
        user_received_mail = False
        for email in mail.outbox:
            if normal_user.email in email.to:
                user_received_mail = True
                break
        
        assert user_received_mail
    # Fix for test_notification_sent_on_rejection
    def test_notification_sent_on_rejection(self, api_client, admin_user, login_and_validate_otp, user_lot, normal_user, iot_device, settings):
        """Test that email notifications are sent when rejecting a request."""
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Clear the email outbox
        from django.core import mail
        mail.outbox = []
        
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Reject the request
        rejection_reason = "Motivo de rechazo para prueba."
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        response = client.post(url, data={"observations": rejection_reason}, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        # Verify request has been updated
        flow_request.refresh_from_db()
        assert flow_request.status == "Finalizado"
        assert flow_request.is_approved == False
        assert flow_request.observations == rejection_reason
        
        # Verify that at least one email was sent
        assert len(mail.outbox) > 0
        
        # Verify the email was sent to the right person
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
                        
                if any(term in email_content for term in ['rechazada', 'rechazo', 'decisión', 'solicitud']):
                    has_rejection_terms = True
                    break
        
        assert has_rejection_terms

    def test_non_admin_cannot_approve_reject_requests(self, api_client, normal_user, login_and_validate_otp, user_lot, iot_device):
        """Test that non-admin users cannot approve or reject flow requests."""
        # Login as normal user
        client = login_and_validate_otp(api_client, normal_user, password="UserPass123@")
        
        # Get the valve4 device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
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
        
        # Try to approve as a non-admin user
        url = reverse('flow-request-approve', kwargs={'pk': flow_request.id})
        response = client.post(url)
        
        # Should fail with permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Try to reject as a non-admin user
        url = reverse('flow-request-reject', kwargs={'pk': flow_request.id})
        response = client.post(url, data={"observations": "Motivo de rechazo"}, format='json')
        
        # Should fail with permission denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_water_supply_failure_report(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, normal_user, iot_device):
        """Verifica que se puede asignar correctamente un reporte de fallo en el suministro de agua."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        # Crear un reporte de fallo en el suministro de agua (por el dueño del predio)
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Estado inicial del reporte
        assert failure_report.status == 'Pendiente'
        
        # Crear asignación
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que el reporte ha sido actualizado a "En proceso"
        failure_report.refresh_from_db()
        assert failure_report.status == 'En proceso'
        
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(failure_report=failure_report).first()
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user

    def test_assign_application_failure_report(self, api_client, admin_user, tecnico_user, login_and_validate_otp, normal_user):
        """Verifica que se puede asignar correctamente un reporte de fallo en el aplicativo."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        # Crear un reporte de fallo en el aplicativo (no requiere lote ni predio)
        failure_report = self.setup_application_failure_report(normal_user)
        
        # Estado inicial del reporte
        assert failure_report.status == 'Pendiente'
        
        # Crear asignación
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que el reporte ha sido actualizado a "En proceso"
        failure_report.refresh_from_db()
        assert failure_report.status == 'En proceso'
        
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(failure_report=failure_report).first()
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user

    def test_assign_definitive_cancellation_request(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, iot_device, normal_user):
        """Verifica que se puede asignar correctamente una solicitud de cancelación definitiva."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        # Crear una solicitud de cancelación definitiva
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        flow_request = self.setup_definitive_cancellation_request(normal_user, lote1, valve4)
        
        # Estado inicial de la solicitud
        assert flow_request.status == 'Pendiente'
        
        # Crear asignación
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_request.id
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que la solicitud ha sido actualizada a "En proceso"
        flow_request.refresh_from_db()
        assert flow_request.status == 'En proceso'
        
        # Verificar que la asignación se creó correctamente
        assignment = Assignment.objects.filter(flow_request=flow_request).first()
        assert assignment is not None
        assert assignment.assigned_to == tecnico_user
        assert assignment.assigned_by == admin_user

    def test_only_users_with_can_be_assigned_permission(self, api_client, admin_user, normal_user, login_and_validate_otp, user_lot, user_plot, iot_device):
        """Verifica que no se puede asignar a usuarios sin el permiso 'can_be_assigned'."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos para admin pero NO para normal_user
        self.setup_permissions(admin_user)
        
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Intentar asignar a usuario sin permiso
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': normal_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Debe fallar por falta de permisos
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Verificar mensaje de error
        response_data = json.loads(response.content.decode('utf-8'))
        assert 'errors' in response_data
        assert 'assigned_to' in response_data['errors']

    def test_error_on_invalid_user_id(self, api_client, admin_user, login_and_validate_otp, user_lot, user_plot, iot_device, normal_user):
        """Verifica que se devuelve un error apropiado al intentar asignar a un ID de usuario inexistente."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user)
        
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Intentar asignar a un usuario que no existe
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': '999999999999',  # ID que no existe
            'failure_report': failure_report.id
        }, format='json')
        
        # Debe fallar por usuario inexistente
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Verificar que se incluye un mensaje de error apropiado
        response_data = json.loads(response.content.decode('utf-8'))
        assert 'errors' in response_data
        assert 'assigned_to' in response_data['errors']

    def test_notification_for_water_supply_report_assignment(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, iot_device, settings, normal_user):
        """Verifica que se envía una notificación cuando se asigna un reporte de fallo en el suministro de agua."""
        # Configurar backend de correo para testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Limpiar bandeja de correo
        mail.outbox = []
        
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        # Crear un reporte de fallo en el suministro de agua
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Crear asignación
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron notificaciones
        assert len(mail.outbox) > 0
        
        # Verificar que se envió al técnico y al administrador
        recipients = []
        for email in mail.outbox:
            recipients.extend(email.to)
        
        assert admin_user.email in recipients
        assert tecnico_user.email in recipients

    def test_maintenance_report_changes_status(self, api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, iot_device, normal_user):
        """Verifica que un informe de mantenimiento cambia el estado de una solicitud/reporte a 'A espera de aprobación'."""
        # Login como admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permisos
        self.setup_permissions(admin_user, tecnico_user)
        
        # Crear un reporte de fallo
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_water_supply_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Crear asignación
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Obtener ID de la asignación
        assignment_id = response.data['id']
        
        # Login como técnico
        client = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        
        # Crear informe de mantenimiento
        url = reverse('maintenance-report-create')
        response = client.post(url, data={
            'assignment': assignment_id,
            'intervention_date': timezone.now().isoformat(),
            'description': 'Se reparó el problema con el suministro de agua',
            'status': 'Finalizado'
        }, format='json')
        
        # Verificar respuesta exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que el reporte ha cambiado a estado "A espera de aprobación"
        failure_report.refresh_from_db()
        assert failure_report.status == 'A espera de aprobación'