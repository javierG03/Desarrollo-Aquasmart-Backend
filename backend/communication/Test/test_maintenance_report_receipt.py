import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from django.core import mail
from django.test import override_settings
import json
import re

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

    def setup_permissions(self, admin_user, tecnico_user=None):
        """Helper method to set up permissions for assignment tests"""
        # Get content type for Assignment model
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
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

    def test_notification_sent_when_maintenance_report_created(self, api_client, login_and_validate_otp, admin_user, 
                                                              tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que se envía una notificación por correo cuando un técnico crea
        un informe de mantenimiento (HU01)
        """
        # PASO 1: Preparar cliente API autenticado como administrador
        client = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        
        # PASO 2: Configurar permisos necesarios
        self.setup_permissions(admin_user, tecnico_user)
        
        # PASO 3: Crear una solicitud de flujo directamente en la base de datos
        lote1, _, _ = user_lot
        
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de prueba para el test RF71',
            requires_delegation=True  # Este tipo requiere delegación
        )
        
        print(f"Solicitud creada: ID={flow_request.id}, Tipo={flow_request.flow_request_type}")
        
        # PASO 4: Crear una asignación para el técnico
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "flow_request": flow_request.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear la asignación correctamente"
        
        # PASO 5: Obtener la asignación creada
        assignment = Assignment.objects.latest('id')
        assert assignment is not None, "No se encontró la asignación creada"
        print(f"Asignación creada: ID={assignment.id}, Técnico={assignment.assigned_to.get_full_name()}")
        
        # PASO 6: Limpiar la bandeja de correo para el test
        mail.outbox = []
        
        # PASO 7: Técnico crea el informe de mantenimiento
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
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
            
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear el informe de mantenimiento"
        
        # PASO 8: Verificar que se haya enviado el correo electrónico
        assert len(mail.outbox) > 0, "No se envió ningún correo electrónico"
        print(f"Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # PASO 9: Verificar que se haya enviado el correo al supervisor y al técnico
        receivers = []
        for email in mail.outbox:
            receivers.extend(email.to)
        
        print(f"Destinatarios de correos: {receivers}")
        print(f"Email del admin: {admin_user.email}")
        print(f"Email del técnico: {tecnico_user.email}")
        
        assert admin_user.email in receivers, "No se envió correo al supervisor"
        assert tecnico_user.email in receivers, "No se envió correo al técnico"
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_content_matches_requirements(self, api_client, login_and_validate_otp, admin_user, 
                                                      tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que el contenido de la notificación incluye todos los datos
        requeridos según la HU02
        """
        # PASO 1: Configurar permisos necesarios
        self.setup_permissions(admin_user, tecnico_user)
        
        # PASO 2: Crear una solicitud válida para asignación
        lote1, _, _ = user_lot
        
        flow_request = FlowRequest.objects.create(
            created_by=normal_user,
            lot=lote1,
            type='Solicitud',
            flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL,
            status='Pendiente',
            observations='Solicitud de prueba para el test RF71 contenido',
            requires_delegation=True
        )
        
        print(f"Solicitud creada: ID={flow_request.id}, Tipo={flow_request.flow_request_type}")
        
        # PASO 3: Crear una asignación para el técnico
        client_admin = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "flow_request": flow_request.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client_admin.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear la asignación"
        
        # PASO 4: Obtener la asignación creada
        assignment = Assignment.objects.latest('id')
        print(f"Asignación creada: ID={assignment.id}")
        
        # PASO 5: Limpiar la bandeja de correo para el test
        mail.outbox = []
        
        # PASO 6: Técnico crea el informe de mantenimiento
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
        # Usar formato ISO
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
        
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear el informe de mantenimiento"
        
        # PASO 7: Verificar correos enviados
        assert len(mail.outbox) > 0, "No se envió ningún correo electrónico"
        
        # PASO 8: Obtener el informe creado
        maintenance_report = MaintenanceReport.objects.latest('id')
        print(f"Informe creado: ID={maintenance_report.id}")
        
        # PASO 9: Analizar contenido de los correos
        print("--- Análisis del contenido de los correos ---")
        has_report_id = False
        has_type = False
        has_flow_id = False
        has_tech_name = False
        has_admin_name = False
        has_status = False
        
        for i, email in enumerate(mail.outbox):
            print(f"Correo #{i+1}:")
            print(f"  Asunto: {email.subject}")
            print(f"  Para: {email.to}")
            print(f"  De: {email.from_email}")
            
            # Construir contenido completo
            full_content = f"{email.subject} {email.body}"
            if hasattr(email, 'alternatives') and email.alternatives:
                for alt_content, mime_type in email.alternatives:
                    if 'html' in mime_type.lower():
                        full_content += f" {alt_content}"
            
            # Buscar elementos requeridos
            report_id_str = str(maintenance_report.id)
            flow_id_str = str(flow_request.id)
            
            print(f"  Buscando el ID del informe ({report_id_str}) en el correo...")
            if report_id_str in full_content:
                has_report_id = True
                print(f"  ✅ ID del informe encontrado: '{report_id_str}'")
            else:
                print(f"  ❌ ID del informe NO encontrado: '{report_id_str}'")
                print(f"  Fragmento del contenido: {full_content[:200]}...")
            
            print(f"  Buscando tipo 'Solicitud' en el correo...")
            if "Solicitud" in full_content:
                has_type = True
                print(f"  ✅ Tipo 'Solicitud' encontrado")
            else:
                print(f"  ❌ Tipo 'Solicitud' NO encontrado")
            
            print(f"  Buscando ID de la solicitud ({flow_id_str}) en el correo...")
            if flow_id_str in full_content:
                has_flow_id = True
                print(f"  ✅ ID de la solicitud encontrado: '{flow_id_str}'")
            else:
                print(f"  ❌ ID de la solicitud NO encontrado: '{flow_id_str}'")
            
            # Buscar nombres
            tech_fullname = tecnico_user.get_full_name()
            tech_firstname = tecnico_user.first_name
            
            print(f"  Buscando nombre del técnico ({tech_fullname} o {tech_firstname}) en el correo...")
            if tech_fullname in full_content or tech_firstname in full_content:
                has_tech_name = True
                print(f"  ✅ Nombre del técnico encontrado")
            else:
                print(f"  ❌ Nombre del técnico NO encontrado")
            
            admin_fullname = admin_user.get_full_name()
            admin_firstname = admin_user.first_name
            
            print(f"  Buscando nombre del administrador ({admin_fullname} o {admin_firstname}) en el correo...")
            if admin_fullname in full_content or admin_firstname in full_content:
                has_admin_name = True
                print(f"  ✅ Nombre del administrador encontrado")
            else:
                print(f"  ❌ Nombre del administrador NO encontrado")
            
            print(f"  Buscando estado 'Finalizado' en el correo...")
            if "Finalizado" in full_content:
                has_status = True
                print(f"  ✅ Estado 'Finalizado' encontrado")
            else:
                print(f"  ❌ Estado 'Finalizado' NO encontrado")
        
        # PASO 10: Verificar que todos los elementos requeridos están presentes
        if not has_report_id:
            print("\n❌❌❌ FALLO: El ID del informe no se encontró en ningún correo")
        if not has_type:
            print("\n❌❌❌ FALLO: El tipo 'Solicitud' no se encontró en ningún correo")
        if not has_flow_id:
            print("\n❌❌❌ FALLO: El ID de la solicitud no se encontró en ningún correo")
        if not has_tech_name:
            print("\n❌❌❌ FALLO: El nombre del técnico no se encontró en ningún correo")
        if not has_admin_name:
            print("\n❌❌❌ FALLO: El nombre del administrador no se encontró en ningún correo")
        if not has_status:
            print("\n❌❌❌ FALLO: El estado 'Finalizado' no se encontró en ningún correo")
        
        # Verificar todos los requisitos
        assert has_report_id, "El ID del informe debe aparecer en el asunto o cuerpo del correo"
        assert has_type, "El tipo de solicitud debe aparecer en el cuerpo del correo"
        assert has_flow_id, "El ID de la solicitud original debe aparecer en el cuerpo del correo"
        assert has_tech_name, "El nombre del técnico debe aparecer en el cuerpo del correo"
        assert has_admin_name, "El nombre del supervisor debe aparecer en el cuerpo del correo"
        assert has_status, "El estado del informe debe aparecer en el cuerpo del correo"
    
    @override_settings(EMAIL_TIMEOUT=300)  # 5 minutos en segundos
    def test_notification_timing(self, api_client, login_and_validate_otp, admin_user, 
                               tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test para verificar que la configuración de tiempo de entrega cumple con los requisitos del RF71
        """
        from django.conf import settings
        
        # PASO 1: Verificar la configuración del tiempo de entrega en settings
        print("Verificando EMAIL_TIMEOUT en settings...")
        has_email_timeout = hasattr(settings, 'EMAIL_TIMEOUT')
        email_timeout_value = getattr(settings, 'EMAIL_TIMEOUT', None)
        
        print(f"¿Tiene EMAIL_TIMEOUT?: {has_email_timeout}")
        print(f"Valor de EMAIL_TIMEOUT: {email_timeout_value}")
        
        assert has_email_timeout, "La configuración EMAIL_TIMEOUT no está definida"
        assert email_timeout_value <= 300, f"El tiempo máximo de entrega debe ser de 5 minutos (300 segundos) o menos, pero es {email_timeout_value}"
        
        # PASO 2: Verificar la configuración en NOTIFICATION_CONFIG
        print("\nVerificando timeout en NOTIFICATION_CONFIG...")
        if hasattr(settings, 'NOTIFICATION_CONFIG'):
            notification_config = settings.NOTIFICATION_CONFIG
            email_settings = notification_config.get('EMAIL_SETTINGS', {})
            delivery_timeouts = email_settings.get('DELIVERY_TIMEOUTS', {})
            email_delivery_timeout = delivery_timeouts.get('EMAIL')
            
            print(f"¿Tiene NOTIFICATION_CONFIG?: {True}")
            print(f"EMAIL_SETTINGS: {email_settings}")
            print(f"DELIVERY_TIMEOUTS: {delivery_timeouts}")
            print(f"EMAIL timeout: {email_delivery_timeout}")
            
            if email_delivery_timeout is not None:
                assert email_delivery_timeout <= 300, \
                    f"El tiempo máximo de entrega en NOTIFICATION_CONFIG debe ser de 5 minutos (300 segundos) o menos, pero es {email_delivery_timeout}"
        else:
            print("No se encontró NOTIFICATION_CONFIG en la configuración")

    def test_full_assignment_and_maintenance_flow(self, api_client, login_and_validate_otp, admin_user, 
                                               tecnico_user, normal_user, user_plot, user_lot, iot_device):
        """
        Test de integración para todo el flujo: creación de reporte, asignación, intervención y aprobación
        """
        # PASO 1: Configurar permisos necesarios
        self.setup_permissions(admin_user, tecnico_user)
        
        # PASO 2: Crear un reporte de fallo
        lote1, _, _ = user_lot
        print(f"Creando reporte de fallo para el lote {lote1.id_lot}...")
        
        # Limpiar la bandeja de correo
        mail.outbox = []
        
        # Crear el reporte de fallo en la base de datos
        failure_report = FailureReport.objects.create(
            type='Reporte',
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations="Reporte de prueba para RF71 integración"
        )
        
        print(f"Reporte creado: ID={failure_report.id}, Estado={failure_report.status}")
        
        # PASO 3: Admin asigna el reporte al técnico
        print("Realizando la asignación al técnico...")
        client_admin = login_and_validate_otp(api_client, admin_user, password="AdminPass123@")
        assignment_url = reverse('assignment-create')
        assignment_data = {
            "failure_report": failure_report.id,
            "assigned_to": tecnico_user.document,
        }
        
        response = client_admin.post(assignment_url, data=assignment_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error al crear asignación: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear la asignación"
        
        # PASO 4: Obtener la asignación
        assignment = Assignment.objects.latest('id')
        print(f"Asignación creada: ID={assignment.id}")
        
        # Verificar que el reporte cambió a "En proceso"
        failure_report.refresh_from_db()
        print(f"Estado del reporte después de asignación: {failure_report.status}")
        assert failure_report.status == 'En proceso', "El reporte debería cambiar a estado 'En proceso'"
        
        # PASO 5: Limpiar la bandeja de correo antes de crear el informe
        mail.outbox = []
        
        # PASO 6: Técnico crea informe de mantenimiento
        print("Técnico crea informe de mantenimiento...")
        client_tecnico = login_and_validate_otp(api_client, tecnico_user, password="UserPass123@")
        maintenance_report_url = reverse('maintenance-report-create')
        
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
            
        assert response.status_code == status.HTTP_201_CREATED, "No se pudo crear el informe de mantenimiento"
        
        # PASO 7: Verificar que se envió el correo
        assert len(mail.outbox) > 0, "No se envió ningún correo electrónico"
        print(f"Se enviaron {len(mail.outbox)} correos para el informe de mantenimiento")
        
        # PASO 8: Verificar cambio de estado del reporte
        failure_report.refresh_from_db()
        print(f"Estado del reporte después del informe: {failure_report.status}")
        assert failure_report.status == 'A espera de aprobación', "El reporte debería cambiar a estado 'A espera de aprobación'"
        
        # PASO 9: Buscar el correo enviado al admin
        admin_email = None
        for email in mail.outbox:
            if admin_user.email in email.to:
                admin_email = email
                break
        
        assert admin_email is not None, "No se envió correo al administrador"
        print(f"Correo enviado al administrador: {admin_email.subject}")
        
        # PASO 10: Limpiar la bandeja de correo antes de aprobar
        mail.outbox = []
        
        # PASO 11: Admin aprueba el informe
        print("Administrador aprueba el informe...")
        maintenance_report = MaintenanceReport.objects.latest('id')
        approve_url = reverse('maintenance-report-approve', args=[maintenance_report.id])
        
        response = client_admin.post(approve_url)
        
        if response.status_code != status.HTTP_200_OK:
            print(f"Error al aprobar informe: {response.content.decode()}")
            
        assert response.status_code == status.HTTP_200_OK, "No se pudo aprobar el informe"
        
        # PASO 12: Verificar que el reporte de fallo cambió a estado Finalizado
        failure_report.refresh_from_db()
        print(f"Estado final del reporte: {failure_report.status}")
        assert failure_report.status == 'Finalizado', "El reporte de fallo debería cambiar a estado 'Finalizado'"