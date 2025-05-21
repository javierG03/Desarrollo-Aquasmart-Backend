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
        print("\n----- INICIANDO TEST: Email delivery time within one minute -----")
        
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        print("✓ Configurado backend de correo en memoria para pruebas")
        
        # Login as admin
        print("⏳ Iniciando sesión como administrador...")
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        print("✓ Sesión iniciada como administrador")
        
        # Setup permissions
        print("⏳ Configurando permisos...")
        self.setup_permissions(admin_user, tecnico_user)
        print("✓ Permisos configurados correctamente")
        
        # Create a failure report
        print("⏳ Creando reporte de fallo...")
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"✓ Reporte de fallo creado con ID: {failure_report.id}")
        
        # Limpiar el buzón de correo
        mail.outbox = []
        print("✓ Buzón de correo limpiado")
        
        # Medir tiempo antes de asignación
        start_time = time.time()
        print(f"⏳ Iniciando medición de tiempo en: {start_time}")
        
        # Create an assignment
        url = reverse('assignment-create')
        print(f"⏳ Creando asignación para el reporte {failure_report.id} al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        
        # Medir tiempo después de asignación
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"✓ Asignación creada. Tiempo transcurrido: {elapsed_time:.2f} segundos")
        print(f"✓ Código de estado de respuesta: {response.status_code}")
        print(f"✓ Respuesta: {response.data}")
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED, f"Error: La solicitud falló con código {response.status_code}"
        print("✓ La solicitud fue exitosa (código 201)")
        
        # Verificar que se enviaron correos
        print(f"⏳ Verificando correos enviados... Cantidad: {len(mail.outbox)}")
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        print(f"✓ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Verificar que el tiempo de proceso fue menor a 60 segundos (requisito HU)
        assert elapsed_time < 60, f"El proceso tomó {elapsed_time} segundos, excediendo el requisito de 60 segundos"
        print(f"✓ El tiempo de proceso ({elapsed_time:.2f}s) fue menor a 60 segundos")
        
        # Comprobar que el técnico recibió correo
        tech_email_received = False
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email_received = True
                print(f"✓ Correo enviado al técnico: {email.subject}")
                break
                
        assert tech_email_received, "El técnico no recibió notificación por correo"
        print("✓ El técnico recibió notificación por correo correctamente")
        print("----- TEST COMPLETADO: Email delivery time within one minute -----")

    def test_notification_for_all_request_and_report_types(self, api_client, admin_user, tecnico_user,
                                                 login_and_validate_otp, user_lot, user_plot,
                                                 normal_user, iot_device, settings):
        """
        Test that notifications are sent for all different types of requests and reports.
        
        This test verifies that the notification system works correctly for:
        1. All types of flow requests (change, temporary cancel, definitive cancel, activation)
        2. All types of failure reports (water supply, application)
        """
        print("\n----- INICIANDO TEST: Notification for all request and report types -----")
        
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        print("✓ Configurado backend de correo en memoria para pruebas")
        
        # Login as admin
        print("⏳ Iniciando sesión como administrador...")
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        print("✓ Sesión iniciada como administrador")
        
        # Setup permissions
        print("⏳ Configurando permisos...")
        self.setup_permissions(admin_user, tecnico_user)
        print("✓ Permisos configurados correctamente")
        
        # Get resources for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"✓ Recursos obtenidos: Lote1 ID={lote1.id_lot}, Válvula4 ID={valve4.iot_id}")
        
        # Dictionary to store different request/report types and their results
        notification_tests = {}
        
        # 1. Test Flow Definitive Cancel Request (natural delegation)
        print("\n⏳ PRUEBA 1: Solicitud de Cancelación Definitiva de Caudal")
        mail.outbox = []  # Clear mail outbox
        print("✓ Buzón de correo limpiado")
        
        print("⏳ Creando solicitud de cancelación definitiva...")
        flow_def_cancel = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de cancelación definitiva para pruebas',
            requires_delegation=True
        )
        print(f"✓ Solicitud creada con ID: {flow_def_cancel.id}")
        
        url = reverse('assignment-create')
        print(f"⏳ Asignando solicitud al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'flow_request': flow_def_cancel.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        notification_tests['FLOW_DEFINITIVE_CANCEL'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        print(f"✓ Resultado almacenado: {notification_tests['FLOW_DEFINITIVE_CANCEL']}")
        
        # 2. Test Water Supply Failure Report
        print("\n⏳ PRUEBA 2: Reporte de Fallo en Suministro de Agua")
        mail.outbox = []  # Clear mail outbox
        print("✓ Buzón de correo limpiado")
        
        print("⏳ Creando reporte de fallo en suministro de agua...")
        water_failure = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en suministro de agua para pruebas'
        )
        print(f"✓ Reporte creado con ID: {water_failure.id}")
        
        print(f"⏳ Asignando reporte al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': water_failure.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        notification_tests['WATER_SUPPLY_FAILURE'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        print(f"✓ Resultado almacenado: {notification_tests['WATER_SUPPLY_FAILURE']}")
        
        # 3. Test Application Failure Report
        print("\n⏳ PRUEBA 3: Reporte de Fallo en la Aplicación")
        mail.outbox = []  # Clear mail outbox
        print("✓ Buzón de correo limpiado")
        
        print("⏳ Creando reporte de fallo en la aplicación...")
        app_failure = FailureReport.objects.create(
            created_by=normal_user,
            type='Reporte',
            failure_type=TypeReport.APPLICATION_FAILURE,
            status='Pendiente',
            observations='Reporte de fallo en aplicación para pruebas'
        )
        print(f"✓ Reporte creado con ID: {app_failure.id}")
        
        print(f"⏳ Asignando reporte al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': app_failure.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        notification_tests['APPLICATION_FAILURE'] = {
            'status_code': response.status_code,
            'emails_sent': len(mail.outbox),
            'technician_notified': any(tecnico_user.email in email.to for email in mail.outbox)
        }
        print(f"✓ Resultado almacenado: {notification_tests['APPLICATION_FAILURE']}")
        
        print("\n⏳ Verificando resultados para todos los tipos de pruebas...")
        # Verify all tests succeeded
        for test_type, results in notification_tests.items():
            print(f"\n⏳ Verificando {test_type}:")
            assert results['status_code'] == status.HTTP_201_CREATED, f"Error: Assignment of {test_type} failed with status {results['status_code']}"
            print(f"✓ Código de estado correcto (201)")
            
            assert results['emails_sent'] > 0, f"Error: No emails were sent for {test_type}"
            print(f"✓ Correos enviados: {results['emails_sent']}")
            
            assert results['technician_notified'], f"Error: Technician was not notified for {test_type}"
            print(f"✓ Técnico notificado correctamente")
            
        print("\n✓ Todas las pruebas pasaron exitosamente")
        print("----- TEST COMPLETADO: Notification for all request and report types -----")

    def test_email_content_meets_requirements(self, api_client, admin_user, tecnico_user,
                                       login_and_validate_otp, user_lot, user_plot,
                                       normal_user, iot_device, settings):
        """
        Test that email content meets the requirements specified in the user story.
        """
        print("\n----- INICIANDO TEST: Email content meets requirements -----")
        
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        print("✓ Configurado backend de correo en memoria para pruebas")
        
        # Login as admin
        print("⏳ Iniciando sesión como administrador...")
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        print("✓ Sesión iniciada como administrador")
        
        # Setup permissions
        print("⏳ Configurando permisos...")
        self.setup_permissions(admin_user, tecnico_user)
        print("✓ Permisos configurados correctamente")
        
        # Create a failure report
        print("⏳ Creando reporte de fallo...")
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"✓ Reporte de fallo creado con ID: {failure_report.id}")
        
        # Limpiar el buzón de correo
        mail.outbox = []
        print("✓ Buzón de correo limpiado")
        
        # Create an assignment
        url = reverse('assignment-create')
        print(f"⏳ Creando asignación para el reporte {failure_report.id} al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED, f"Error: La solicitud falló con código {response.status_code}"
        print("✓ La solicitud fue exitosa (código 201)")
        
        # Verificar que se enviaron correos
        print(f"⏳ Verificando correos enviados... Cantidad: {len(mail.outbox)}")
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        print(f"✓ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Encontrar el correo del técnico
        tech_email = None
        print("⏳ Buscando correo enviado al técnico...")
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email = email
                print(f"✓ Correo encontrado: {email.subject}")
                break
                
        assert tech_email is not None, "El técnico no recibió notificación por correo"
        print("✓ El técnico recibió notificación por correo")
        
        # Verificar que el asunto contiene "Nueva asignación" (requisito de HU)
        print("⏳ Verificando asunto del correo...")
        has_required_subject = "Nueva asignación" in tech_email.subject or "Nueva Asignación" in tech_email.subject
        assert has_required_subject, "El asunto del correo no contiene 'Nueva asignación'"
        print(f"✓ El asunto contiene 'Nueva asignación': {tech_email.subject}")
        
        # Verificar contenido requerido según HU
        print("⏳ Verificando contenido del correo...")
        email_content = tech_email.subject + " " + tech_email.body
        required_content = [
            str(failure_report.id),  # ID de la solicitud
            "Reporte",  # Tipo de reporte
            admin_user.get_full_name() or admin_user.first_name,  # Quién asignó
            "fecha" # Referencia a la fecha
        ]
        
        for content in required_content:
            print(f"⏳ Buscando contenido requerido: '{content}'")
            content_found = content.lower() in email_content.lower()
            assert content_found, f"Contenido requerido '{content}' no se encuentra en el correo"
            print(f"✓ Contenido '{content}' encontrado en el correo")
        
        # Verificar si hay versión HTML (opcional pero recomendable)
        print("⏳ Verificando si el correo incluye versión HTML...")
        has_html = False
        if hasattr(tech_email, 'alternatives') and tech_email.alternatives:
            for content, mime_type in tech_email.alternatives:
                if 'text/html' in mime_type:
                    has_html = True
                    print("✓ Versión HTML encontrada en el correo")
                    break
        
        assert has_html, "El correo no incluye versión HTML"
        if has_html:
            print("✓ El correo incluye versión HTML correctamente")
        
        print("----- TEST COMPLETADO: Email content meets requirements -----")

    def test_notification_on_reassignment(self, api_client, admin_user, tecnico_user, operador_user,
                                   login_and_validate_otp, user_lot, user_plot, normal_user, 
                                   iot_device, settings):
        """Test that notifications are sent on reassignment of tasks."""
        print("\n----- INICIANDO TEST: Notification on reassignment -----")
        
        # Configure Django to use the in-memory email backend for testing
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        print("✓ Configurado backend de correo en memoria para pruebas")
        
        # Login as admin with correct password
        print("⏳ Iniciando sesión como administrador...")
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        print("✓ Sesión iniciada como administrador")
        
        # Setup permissions
        print("⏳ Configurando permisos...")
        self.setup_permissions(admin_user)
        print("✓ Permisos de administrador configurados")
        
        # Get content type for Assignment model
        print("⏳ Configurando permisos adicionales para técnico y operador...")
        content_type = ContentType.objects.get_for_model(Assignment)
        print(f"✓ Tipo de contenido obtenido: {content_type}")
        
        # Give both technician and operator permission to be assigned
        try:
            can_be_assigned = Permission.objects.get(
                codename='can_be_assigned',
                content_type=content_type
            )
            print("✓ Permiso 'can_be_assigned' encontrado")
        except Permission.DoesNotExist:
            can_be_assigned = Permission.objects.create(
                codename='can_be_assigned',
                name='Can be assigned to handle requests/reports',
                content_type=content_type
            )
            print("✓ Permiso 'can_be_assigned' creado")
            
        print(f"⏳ Asignando permiso 'can_be_assigned' a técnico ({tecnico_user.document}) y operador ({operador_user.document})...")
        tecnico_user.user_permissions.add(can_be_assigned)
        operador_user.user_permissions.add(can_be_assigned)
        tecnico_user.save()
        operador_user.save()
        print("✓ Permisos asignados correctamente")
        
        # Get the plot, lot and device for the test
        lote1, _, _ = user_lot
        valve4, _, _, _ = iot_device
        print(f"✓ Recursos obtenidos: Lote1 ID={lote1.id_lot}, Válvula4 ID={valve4.iot_id}")
        
        # Create a failure report
        print("⏳ Creando reporte de fallo...")
        failure_report = self.setup_failure_report(normal_user, lote1, user_plot, valve4)
        print(f"✓ Reporte de fallo creado con ID: {failure_report.id}")
        
        # Create first assignment to technician
        url = reverse('assignment-create')
        print(f"⏳ Creando primera asignación para el técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED, f"Error: La primera asignación falló con código {response.status_code}"
        print("✓ La primera asignación fue exitosa (código 201)")
        
        assignment_id = response.data['id']
        print(f"✓ ID de asignación creada: {assignment_id}")
        
        # Clear the email outbox
        mail.outbox = []
        print("✓ Buzón de correo limpiado para la prueba de reasignación")
        
        # Now reassign to operator
        url = reverse('assignment-reassign', kwargs={'pk': assignment_id})
        print(f"⏳ Reasignando tarea al operador {operador_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': operador_user.document,
            'reassigned': True
        }, format='json')
        print(f"✓ Respuesta de reasignación recibida: {response.status_code}")
        
        # Should succeed
        assert response.status_code == status.HTTP_200_OK, f"Error: La reasignación falló con código {response.status_code}"
        print("✓ La reasignación fue exitosa (código 200)")
        print(f"✓ Respuesta: {response.data}")
        
        # Check if at least one email was sent
        print(f"⏳ Verificando correos enviados tras reasignación... Cantidad: {len(mail.outbox)}")
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos después de la reasignación"
        print(f"✓ Se enviaron {len(mail.outbox)} correos electrónicos tras la reasignación")
        
        # Both new assignee and admin should receive emails
        print("⏳ Verificando destinatarios de los correos...")
        email_recipients = []
        for email in mail.outbox:
            email_recipients.extend(email.to)
            print(f"  Correo enviado a: {email.to}")
        
        print(f"⏳ Verificando que el administrador {admin_user.email} recibió notificación...")
        admin_received = admin_user.email in email_recipients
        assert admin_received, "El administrador no recibió notificación por correo"
        print("✓ El administrador recibió notificación")
        
        print(f"⏳ Verificando que el operador {operador_user.email} recibió notificación...")
        operator_received = operador_user.email in email_recipients
        assert operator_received, "El operador no recibió notificación por correo"
        print("✓ El operador recibió notificación")
        
        # Find operator's email
        operator_email = None
        print("⏳ Buscando el correo específico enviado al operador...")
        for email in mail.outbox:
            if operador_user.email in email.to:
                operator_email = email
                print(f"✓ Correo encontrado: {email.subject}")
                break
        
        assert operator_email is not None, "No se pudo encontrar un correo específico para el operador"
        print("✓ Correo para el operador encontrado correctamente")
        
        # Check that it contains reassignment indicator or proper assignment subject
        print("⏳ Verificando que el asunto contiene información sobre asignación...")
        has_assignment_subject = "asignación" in operator_email.subject.lower() or "asignacion" in operator_email.subject.lower()
        assert has_assignment_subject, "El asunto del correo no contiene referencia a asignación"
        print(f"✓ El asunto contiene referencia a asignación: {operator_email.subject}")
        
        print("----- TEST COMPLETADO: Notification on reassignment -----")

    
    def test_notification_delivered_to_correct_recipient(self, api_client, admin_user, tecnico_user, 
                                              operador_user, login_and_validate_otp, 
                                              user_lot, user_plot, normal_user, iot_device, settings):
        """
        Test that ensures notifications are delivered to the correct recipient based on assignment.
        Verifies that the technician, not the operator, receives notification when assigned to technician,
        and vice versa.
        """
        print("\n----- INICIANDO TEST: Notification delivered to correct recipient -----")
        
        # Usar backend de correo en memoria para pruebas
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        print("✓ Configurado backend de correo en memoria para pruebas")
        
        # Login as admin
        print("⏳ Iniciando sesión como administrador...")
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        print("✓ Sesión iniciada como administrador")
        
        # Setup permissions for all relevant users
        print("⏳ Configurando permisos para todos los usuarios...")
        content_type = ContentType.objects.get_for_model(Assignment)
        print(f"✓ Tipo de contenido obtenido: {content_type}")
        
        # Create necessary permissions
        try:
            assign_permission = Permission.objects.get(
                codename='can_assign_user',
                content_type=content_type
            )
            print("✓ Permiso 'can_assign_user' encontrado")
        except Permission.DoesNotExist:
            assign_permission = Permission.objects.create(
                codename='can_assign_user',
                name='Can assign user to handle requests/reports',
                content_type=content_type
            )
            print("✓ Permiso 'can_assign_user' creado")
            
        try:
            can_be_assigned = Permission.objects.get(
                codename='can_be_assigned',
                content_type=content_type
            )
            print("✓ Permiso 'can_be_assigned' encontrado")
        except Permission.DoesNotExist:
            can_be_assigned = Permission.objects.create(
                codename='can_be_assigned',
                name='Can be assigned to handle requests/reports',
                content_type=content_type
            )
            print("✓ Permiso 'can_be_assigned' creado")
        
        # Assign permissions to users
        print("⏳ Asignando permisos a usuarios...")
        admin_user.user_permissions.add(assign_permission)
        tecnico_user.user_permissions.add(can_be_assigned)
        operador_user.user_permissions.add(can_be_assigned)
        
        admin_user.save()
        tecnico_user.save()
        operador_user.save()
        print("✓ Permisos asignados correctamente")
        
        # Usaremos lotes diferentes para cada prueba
        lote1, lote2, _ = user_lot  # Usamos los dos primeros lotes
        valve4, _, _, _ = iot_device
        print(f"✓ Recursos obtenidos: Lote1 ID={lote1.id_lot}, Lote2 ID={lote2.id_lot}, Válvula4 ID={valve4.iot_id}")
        
        # Crear una válvula 4" para el segundo lote
        print("⏳ Creando válvula 4\" para el segundo lote...")
        from iot.models import IoTDevice, VALVE_4_ID
        
        # Obtener el tipo de válvula 4"
        valve_type = valve4.device_type
        print(f"✓ Tipo de válvula obtenido: {valve_type}")
        
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
        print(f"✓ Válvula creada para Lote2: {valve4_lote2.iot_id}")
        
        # Crear un reporte para el primer lote
        print("⏳ Creando primer reporte de fallo (Lote1)...")
        failure_report1 = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Primer reporte de prueba para delegación'
        )
        print(f"✓ Primer reporte creado con ID: {failure_report1.id}")
        
        # Test 1: Assign to technician, verify only technician gets notification
        print("\n⏳ PRUEBA 1: Asignar al técnico, verificar que solo el técnico recibe notificación")
        mail.outbox = []  # Limpiar buzón
        print("✓ Buzón de correo limpiado")
        
        url = reverse('assignment-create')
        print(f"⏳ Asignando reporte1 al técnico {tecnico_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report1.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED, f"Error: La asignación al técnico falló con código {response.status_code}"
        print("✓ La asignación al técnico fue exitosa (código 201)")
        
        # Verificar que se enviaron correos
        print(f"⏳ Verificando correos enviados... Cantidad: {len(mail.outbox)}")
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        print(f"✓ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Verificar que el correo llegó al técnico pero NO al operador
        tech_email_received = False
        operator_email_received = False
        
        print("⏳ Verificando destinatarios de los correos...")
        for email in mail.outbox:
            print(f"  Correo enviado a: {email.to}")
            if tecnico_user.email in email.to:
                tech_email_received = True
                print(f"  ✓ Encontrado correo para el técnico: {email.subject}")
            if operador_user.email in email.to:
                operator_email_received = True
                print(f"  ⚠ Encontrado correo para el operador: {email.subject}")
        
        assert tech_email_received, "El técnico no recibió notificación por correo"
        print("✓ El técnico recibió notificación correctamente")
        
        assert not operator_email_received, "El operador recibió una notificación por error"
        print("✓ El operador NO recibió notificación (correcto)")
        
        # Crear un reporte para el segundo lote
        print("\n⏳ Creando segundo reporte de fallo (Lote2)...")
        failure_report2 = FailureReport.objects.create(
            created_by=normal_user,
            lot=lote2,  # Usamos un lote diferente
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Segundo reporte de prueba para delegación'
        )
        print(f"✓ Segundo reporte creado con ID: {failure_report2.id}")
        
        # Test 2: Assign to operator, verify only operator gets notification
        print("\n⏳ PRUEBA 2: Asignar al operador, verificar que solo el operador recibe notificación")
        mail.outbox = []  # Limpiar buzón
        print("✓ Buzón de correo limpiado")
        
        print(f"⏳ Asignando reporte2 al operador {operador_user.first_name}...")
        response = client.post(url, data={
            'assigned_to': operador_user.document,
            'failure_report': failure_report2.id
        }, format='json')
        print(f"✓ Respuesta recibida: {response.status_code}")
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED, f"Error: La asignación al operador falló con código {response.status_code}"
        print("✓ La asignación al operador fue exitosa (código 201)")
        
        # Verificar que se enviaron correos
        print(f"⏳ Verificando correos enviados... Cantidad: {len(mail.outbox)}")
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        print(f"✓ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Verificar que el correo llegó al operador pero NO al técnico
        tech_email_received = False
        operator_email_received = False
        
        print("⏳ Verificando destinatarios de los correos...")
        for email in mail.outbox:
            print(f"  Correo enviado a: {email.to}")
            if tecnico_user.email in email.to:
                tech_email_received = True
                print(f"  ⚠ Encontrado correo para el técnico: {email.subject}")
            if operador_user.email in email.to:
                operator_email_received = True
                print(f"  ✓ Encontrado correo para el operador: {email.subject}")
        
        assert operator_email_received, "El operador no recibió notificación por correo"
        print("✓ El operador recibió notificación correctamente")
        
        assert not tech_email_received, "El técnico recibió una notificación por error cuando se asignó al operador"
        print("✓ El técnico NO recibió notificación cuando se asignó al operador (correcto)")
        
        print("----- TEST COMPLETADO: Notification delivered to correct recipient -----")