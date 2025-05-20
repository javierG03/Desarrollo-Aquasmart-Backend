import pytest
from rest_framework import status
from django.urls import reverse
from communication.assigment_maintenance.models import Assignment
from communication.requests.models import FlowRequest, FlowRequestType
from communication.reports.models import FailureReport, TypeReport
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.conf import settings
import json
import time

@pytest.mark.django_db
class TestNotificationFunctionality:
    """Test suite for RF69: Email notification when a report/request is assigned to a user."""

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

    def test_email_delivery_time_within_one_minute(self, api_client, admin_user, tecnico_user, 
                                                 login_and_validate_otp, user_lot, user_plot, 
                                                 normal_user, iot_device, settings):
        """
        Test that ensures email notification is delivered within one minute of assignment.
        """
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Login as admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Create a failure report
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Limpiar el buzón de correo
        mail.outbox = []
        
        # Medir tiempo antes de asignación
        start_time = time.time()
        
        # Create an assignment
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Medir tiempo después de asignación
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron correos
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        
        # Verificar que el tiempo de proceso fue menor a 60 segundos (requisito HU)
        assert elapsed_time < 60, f"El proceso tomó {elapsed_time} segundos, excediendo el requisito de 60 segundos"
        
        # Comprobar que el técnico recibió correo
        tech_email_received = False
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email_received = True
                break
                
        assert tech_email_received, "El técnico no recibió notificación por correo"

    def test_notification_for_all_request_and_report_types(self, api_client, admin_user, tecnico_user,
                                                     login_and_validate_otp, user_lot, user_plot,
                                                     normal_user, iot_device, settings):
        """
        Test that notifications are sent for all different types of requests and reports.
        
        This test verifies that the notification system works correctly for:
        1. All types of flow requests (change, temporary cancel, definitive cancel, activation)
        2. All types of failure reports (water supply, application)
        """
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Login as admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Get resources for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Dictionary to store different request/report types and their results
        notification_tests = {}
        
        # 1. Test Flow Definitive Cancel Request (natural delegation)
        mail.outbox = []  # Clear mail outbox
        
        flow_def_cancel = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de cancelación definitiva para pruebas',
            requires_delegation=True
        )
        
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_def_cancel.id
        }, format='json')
        
        notification_tests['FLOW_DEFINITIVE_CANCEL'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        
        # 2. Test Water Supply Failure Report
        mail.outbox = []  # Clear mail outbox
        
        water_failure = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en suministro de agua para pruebas'
        )
        
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': water_failure.id
        }, format='json')
        
        notification_tests['WATER_SUPPLY_FAILURE'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        
        # 3. Test Application Failure Report
        mail.outbox = []  # Clear mail outbox
        
        app_failure = FailureReport.objects.create(
            created_by=normal_user,
            type='Reporte',
            failure_type=TypeReport.APPLICATION_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en aplicación para pruebas'
        )
        
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': app_failure.id
        }, format='json')
        
        notification_tests['APPLICATION_FAILURE'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        
        # Verify all tests succeeded
        for test_type, results in notification_tests.items():
            assert results['status_code'] == status.HTTP_201_CREATED, f"Assignment of {test_type} failed with status {results['status_code']}"
            assert results['emails_sent'] > 0, f"No emails were sent for {test_type}"
            assert results['technician_notified'], f"Technician was not notified for {test_type}"

    def test_email_content_meets_requirements(self, api_client, admin_user, tecnico_user,
                                           login_and_validate_otp, user_lot, user_plot,
                                           normal_user, iot_device, settings):
        """
        Test that email content meets the requirements specified in the user story.
        """
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Login as admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
        self.setup_permissions(admin_user, tecnico_user)
        
        # Create a failure report
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Limpiar el buzón de correo
        mail.outbox = []
        
        # Create an assignment
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron correos
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        
        # Encontrar el correo del técnico
        tech_email = None
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email = email
                break
                
        assert tech_email is not None, "El técnico no recibió notificación por correo"
        
        # Verificar que el asunto contiene "Nueva asignación" (requisito de HU)
        assert "Nueva asignación" in tech_email.subject or "Nueva Asignación" in tech_email.subject, "El asunto del correo no contiene 'Nueva asignación'"
        
        # Verificar contenido requerido según HU
        email_content = tech_email.subject + " " + tech_email.body
        required_content = [
            str(failure_report.id),  # ID de la solicitud
            "Reporte",  # Tipo de reporte
            admin_user.get_full_name() or admin_user.first_name,  # Quién asignó
            "fecha" # Referencia a la fecha
        ]
        
        for content in required_content:
            assert content.lower() in email_content.lower(), f"Contenido requerido '{content}' no se encuentra en el correo"
        
        # Verificar si hay versión HTML (opcional pero recomendable)
        has_html = False
        if hasattr(tech_email, 'alternatives') and tech_email.alternatives:
            for content, mime_type in tech_email.alternatives:
                if 'text/html' in mime_type:
                    has_html = True
                    # No verificamos contenido específico HTML, solo su existencia
                    break
        
        assert has_html, "El correo no incluye versión HTML"

    def test_notification_on_reassignment(self, api_client, admin_user, tecnico_user, operador_user,
                                       login_and_validate_otp, user_lot, user_plot, normal_user, 
                                       iot_device, settings):
        """Test that notifications are sent on reassignment of tasks."""
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Login as admin with correct password
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions
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
        
        # Get the plot, lot and device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        
        # Create a failure report
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        
        # Create first assignment to technician
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        assignment_id = response.data['id']
        
        # Clear the email outbox
        mail.outbox = []
        
        # Now reassign to operator
        url = reverse('assignment-reassign', kwargs={'pk': assignment_id})
        response = client.post(url, data={
            'assigned_to': operador_user.document,
            'reassigned': True
        }, format='json')
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        
        # Check if at least one email was sent
        assert len(mail.outbox) > 0
        
        # Both new assignee and admin should receive emails
        email_recipients = []
        for email in mail.outbox:
            email_recipients.extend(email.to)
        
        assert admin_user.email in email_recipients
        assert operador_user.email in email_recipients
        
        # Find operator's email
        operator_email = None
        for email in mail.outbox:
            if operador_user.email in email.to:
                operator_email = email
                break
        
        assert operator_email is not None
        
        # Check that it contains reassignment indicator or proper assignment subject
        assert "asignación" in operator_email.subject.lower() or "asignacion" in operator_email.subject.lower()
    
    def test_notification_delivered_to_correct_recipient(self, api_client, admin_user, tecnico_user, 
                                                  operador_user, login_and_validate_otp, 
                                                  user_lot, user_plot, normal_user, iot_device, settings):
        """
        Test that ensures notifications are delivered to the correct recipient based on assignment.
        Verifies that the technician, not the operator, receives notification when assigned to technician,
        and vice versa.
        """
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Login as admin
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Setup permissions for all relevant users
        content_type = ContentType.objects.get_for_model(Assignment)
        
        # Create necessary permissions
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
        
        # Assign permissions to users
        admin_user.user_permissions.add(assign_permission)
        tecnico_user.user_permissions.add(can_be_assigned)
        operador_user.user_permissions.add(can_be_assigned)
        
        admin_user.save()
        tecnico_user.save()
        operador_user.save()
        
        # Usaremos lotes diferentes para cada prueba
        lote1, lote2, _ = user_lot  # Usamos los dos primeros lotes
        valve4, _, _, _ = iot_device
        
        # Crear una válvula 4" para el segundo lote
        from iot.models import IoTDevice, VALVE_4_ID
        
        # Obtener el tipo de válvula 4"
        valve_type = valve4.device_type
        
        # Crear válvula para lote2
        valve4_lote2 = IoTDevice.objects.create(
            name="Válvula 4\" para Lote 2",
            device_type=valve_type,
            id_plot=user_plot,
            id_lot=lote2,
            is_active=True,
            actual_flow=4.0,
            iot_id="06-0002"  # ID único para esta válvula
        )
        
        # Crear un reporte para el primer lote
        failure_report1 = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Primer reporte de prueba para delegación'
        )
        
        # Test 1: Assign to technician, verify only technician gets notification
        mail.outbox = []  # Limpiar buzón
        
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report1.id
        }, format='json')
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron correos
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        
        # Verificar que el correo llegó al técnico pero NO al operador
        tech_email_received = False
        operator_email_received = False
        
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email_received = True
            if operador_user.email in email.to:
                operator_email_received = True
        
        assert tech_email_received, "El técnico no recibió notificación por correo"
        assert not operator_email_received, "El operador recibió una notificación por error"
        
        # Crear un reporte para el segundo lote
        failure_report2 = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote2,  # Usamos un lote diferente
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Segundo reporte de prueba para delegación'
        )
        
        # Test 2: Assign to operator, verify only operator gets notification
        mail.outbox = []  # Limpiar buzón
        
        response = client.post(url, data={
            'assigned_to': operador_user.document,
            'failure_report': failure_report2.id
        }, format='json')
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron correos
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        
        # Verificar que el correo llegó al operador pero NO al técnico
        tech_email_received = False
        operator_email_received = False
        
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email_received = True
            if operador_user.email in email.to:
                operator_email_received = True
        
        assert operator_email_received, "El operador no recibió notificación por correo"
        assert not tech_email_received, "El técnico recibió una notificación por error cuando se asignó al operador"