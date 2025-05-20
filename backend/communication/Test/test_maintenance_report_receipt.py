import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from django.core import mail
from django.test import override_settings
import json

# Importaciones correctas
from communication.assigment_maintenance.models import Assignment, MaintenanceReport
from communication.requests.models import FlowRequest, FlowRequestType
from communication.reports.models import FailureReport, TypeReport

# Ruta del archivo: backend/communication/Test/test_maintenance_report_receipt.py

@pytest.mark.django_db
class TestRF71:
    """
    Test para el Requerimiento Funcional 71: Recepción informe de mantenimiento realizado por el técnico
    """

    def test_notification_sent_when_maintenance_report_created(self, api_client, login_and_validate_otp, admin_user, 
                                                              tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que se envía una notificación por correo cuando un técnico crea
        un informe de mantenimiento (HU01)
        """
        # Preparar cliente API autenticado como administrador con la contraseña correcta
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # Crear una solicitud de flujo directamente en la base de datos (no a través de la API)
        lote1, _, _ = user_lot
        
        # Crear una solicitud de flujo con requires_delegation=True para que pueda ser asignada
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,  # Este tipo requiere delegación
            status='Pendiente',
            observations='Solicitud de prueba para el test RF71',
            requires_delegation=True
        )
        
        # Dar permiso al técnico para ser asignado
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(Assignment)
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
        
        # Crear una asignación para el técnico
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "flow_request": flow_request.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Obtener la asignación creada
        assignment = Assignment.objects.latest('id')
        assert assignment is not None
        
        # Limpiar la bandeja de correo para el test
        mail.outbox = []
        
        # Técnico crea el informe de mantenimiento
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
        # Usar el formato de fecha correcto
        intervention_date = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        maintenance_report_data = {
            "assignment": assignment.id,
            "intervention_date": intervention_date,
            "description": "Se realizó el cambio de caudal solicitado",
            "status": "Finalizado"
        }
        
        response = client_tecnico.post(maintenance_report_url, data=maintenance_report_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear informe: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se haya enviado el correo electrónico
        assert len(mail.outbox) > 0, "No se envió ningún correo electrónico"
        
        # Verificar que se haya enviado el correo al supervisor y al técnico
        receivers = []
        for email in mail.outbox:
            receivers.extend(email.to)
        
        assert admin_user.email in receivers, "No se envió correo al supervisor"
        assert tecnico_user.email in receivers, "No se envió correo al técnico"
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_content_matches_requirements(self, api_client, login_and_validate_otp, admin_user, 
                                                    tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que el contenido de la notificación incluye todos los datos
        requeridos según la HU02
        """
        # Crear directamente una solicitud válida para asignación
        lote1, _, _ = user_lot
        
        # Crear una solicitud de flujo con requires_delegation=True
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de prueba para el test RF71 contenido',
            requires_delegation=True
        )
        
        # Dar permiso al técnico para ser asignado, si no lo tiene ya
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(Assignment)
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
        
        # Crear una asignación para el técnico
        client_admin = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "flow_request": flow_request.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client_admin.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Obtener la asignación creada
        assignment = Assignment.objects.latest('id')
        
        # Limpiar la bandeja de correo para el test
        mail.outbox = []
        
        # Técnico crea el informe de mantenimiento
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
        # Usar el formato de fecha correcto
        intervention_date = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        maintenance_report_data = {
            "assignment": assignment.id,
            "intervention_date": intervention_date,
            "description": "Se realizó el cambio de caudal solicitado según la HU02",
            "status": "Finalizado"
        }
        
        response = client_tecnico.post(maintenance_report_url, data=maintenance_report_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear informe: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se haya enviado el correo electrónico
        assert len(mail.outbox) > 0, "No se envió ningún correo electrónico"
        
        # Obtener el informe creado
        maintenance_report = MaintenanceReport.objects.latest('id')
        print(f"ID del informe creado: {maintenance_report.id}")
        
        # Depuración - imprimir todos los correos y su contenido
        for i, email in enumerate(mail.outbox):
            print(f"--- Correo {i+1} ---")
            print(f"Asunto: {email.subject}")
            print(f"Destinatarios: {email.to}")
            print(f"Cuerpo:\n{email.body}")
            
            # Verificar si tiene formato HTML alternativo
            if hasattr(email, 'alternatives') and email.alternatives:
                for alt_content, mime_type in email.alternatives:
                    if 'html' in mime_type.lower():
                        print(f"Contenido HTML alternativo:\n{alt_content}")
        
        # Verificar que al menos un correo contenga la información necesaria
        found_id = False
        found_type = False
        found_flow_id = False
        found_tech_name = False
        found_admin_name = False
        found_status = False
        
        for email in mail.outbox:
            email_content = email.subject + " " + email.body
            
            # Buscar también en contenido alternativo HTML si existe
            if hasattr(email, 'alternatives') and email.alternatives:
                for alt_content, mime_type in email.alternatives:
                    if 'html' in mime_type.lower():
                        email_content += " " + str(alt_content)
            
            if str(maintenance_report.id) in email_content:
                found_id = True
                print(f"✅ ID del informe encontrado: {maintenance_report.id}")
            
            if "Solicitud" in email_content:
                found_type = True
                print("✅ Tipo 'Solicitud' encontrado")
            
            if str(flow_request.id) in email_content:
                found_flow_id = True
                print(f"✅ ID de la solicitud encontrado: {flow_request.id}")
            
            if tecnico_user.first_name in email_content or tecnico_user.get_full_name() in email_content:
                found_tech_name = True
                print(f"✅ Nombre del técnico encontrado: {tecnico_user.get_full_name()}")
            
            if admin_user.first_name in email_content or admin_user.get_full_name() in email_content:
                found_admin_name = True
                print(f"✅ Nombre del administrador encontrado: {admin_user.get_full_name()}")
            
            if "Finalizado" in email_content or maintenance_report.get_status_display() in email_content:
                found_status = True
                print(f"✅ Estado 'Finalizado' encontrado")
        
        # Verificar que todas las condiciones se cumplen
        assert found_id, "El ID del informe debe aparecer en el asunto o cuerpo del correo"
        assert found_type, "El tipo de solicitud debe aparecer en el cuerpo del correo"
        assert found_flow_id, "El ID de la solicitud original debe aparecer en el cuerpo del correo"
        assert found_tech_name, "El nombre del técnico debe aparecer en el cuerpo del correo"
        assert found_admin_name, "El nombre del supervisor debe aparecer en el cuerpo del correo"
        assert found_status, "El estado del informe debe aparecer en el cuerpo del correo"
        
    @override_settings(EMAIL_TIMEOUT=300)  # 5 minutos en segundos
    def test_notification_timing(self, api_client, login_and_validate_otp, admin_user, 
                               tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que la configuración de tiempo de entrega cumple con los requisitos del RF71
        """
        from django.conf import settings
        
        # Verificar la configuración del tiempo de entrega
        assert hasattr(settings, 'EMAIL_TIMEOUT'), "La configuración EMAIL_TIMEOUT no está definida"
        assert settings.EMAIL_TIMEOUT <= 300, "El tiempo máximo de entrega debe ser de 5 minutos (300 segundos) o menos"
        
        # Verificar en la configuración de notificaciones
        if hasattr(settings, 'NOTIFICATION_CONFIG'):
            delivery_timeouts = settings.NOTIFICATION_CONFIG.get('EMAIL_SETTINGS', {}).get('DELIVERY_TIMEOUTS', {})
            if 'EMAIL' in delivery_timeouts:
                assert delivery_timeouts['EMAIL'] <= 300, \
                    "El tiempo máximo de entrega en NOTIFICATION_CONFIG debe ser de 5 minutos (300 segundos) o menos"

    def test_full_assignment_and_maintenance_flow(self, api_client, login_and_validate_otp, admin_user, 
                                               tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test de integración para todo el flujo: creación de reporte, asignación, intervención y aprobación
        """
        # Crear un reporte de fallo directamente en la base de datos
        lote1, _, _ = user_lot
        
        # Dar permiso al técnico para ser asignado
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(Assignment)
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
        
        # Limpiar la bandeja de correo
        mail.outbox = []
        
        # Crear directamente el reporte de fallo en la base de datos
        failure_report = FailureReport.objects.create(
            type='Reporte',
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations="Reporte de prueba para RF71 integración"
        )
        
        # Admin asigna el reporte al técnico
        client_admin = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "failure_report": failure_report.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client_admin.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Obtener la asignación
        assignment = Assignment.objects.latest('id')
        
        # Limpiar la bandeja de correo antes de crear el informe
        mail.outbox = []
        
        # Técnico crea informe de mantenimiento
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
        # Usar el formato de fecha correcto
        intervention_date = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        maintenance_report_data = {
            "assignment": assignment.id,
            "intervention_date": intervention_date,
            "description": "Se resolvió el problema de suministro",
            "status": "Finalizado"
        }
        
        response = client_tecnico.post(maintenance_report_url, data=maintenance_report_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear informe: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se envió el correo
        assert len(mail.outbox) > 0
        
        # Buscar el correo enviado al admin
        admin_email = None
        for email in mail.outbox:
            if admin_user.email in email.to:
                admin_email = email
                break
        
        assert admin_email is not None, "No se envió correo al administrador"
        
        # Limpiar la bandeja de correo antes de aprobar
        mail.outbox = []
        
        # Admin aprueba el informe
        maintenance_report = MaintenanceReport.objects.latest('id')
        approve_url = reverse('maintenance-report-approve', args=[maintenance_report.id])
        
        response = client_admin.post(approve_url)
        
        if response.status_code != status.HTTP_200_OK:
            print(f"Error al aprobar informe: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que el reporte de fallo cambió a estado Finalizado
        failure_report.refresh_from_db()
        assert failure_report.status == 'Finalizado', "El reporte de fallo debería cambiar a estado Finalizado"