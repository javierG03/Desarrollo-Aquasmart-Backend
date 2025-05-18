# tests/test_notifications_rf67.py

import pytest
from django.core import mail
from django.utils import timezone
from communication.notifications import (
    send_flow_request_created_notification,
    send_failure_report_created_notification
)
from communication.requests.models import FlowRequest, FlowRequestType
from communication.reports.models import FailureReport, TypeReport
from django.urls import reverse

@pytest.mark.django_db
class TestNotificationRF67:
    """Pruebas para el requerimiento RF67 - Notificación por correo al encargado de recepción"""

    def test_flow_request_notification_to_admin(self, normal_user, user_lot, admin_user, iot_device):
        """
        Verifica que cuando un usuario normal crea una solicitud de caudal,
        se notifica al administrador del sistema.
        """
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        # Limpiar bandeja de salida de correos antes de la prueba
        mail.outbox = []
        
        # Crear solicitud de cambio de caudal
        flow_request = FlowRequest.objects.create(
            type='Solicitud',
            created_by=normal_user,
            lot=lote1,  # Este lote ya tiene la válvula 4" asociada
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            requested_flow=5.0,
            status='Pendiente',
            observations='Solicitud de prueba para test'
        )
        
        # Verificar que se ha enviado al menos un correo
        assert len(mail.outbox) > 0, "No se envió ningún correo tras crear la solicitud"
        
        # Buscar correo dirigido al administrador
        admin_received_email = False
        admin_email = None
        
        for email in mail.outbox:
            if admin_user.email in email.to:
                admin_received_email = True
                admin_email = email
                break
        
        # Verificar que el administrador recibió la notificación
        assert admin_received_email, f"El administrador ({admin_user.email}) no recibió notificación"
        
        # Verificar contenido del correo enviado al administrador
        if admin_email:
            # Verificar que el asunto es claro
            assert "Solicitud" in admin_email.subject or "Nueva" in admin_email.subject
            
            # Verificar TODOS los elementos requeridos en el contenido según la HU:
            email_body = admin_email.body
            
            # 1. Verificar el tipo de solicitud
            assert flow_request.get_flow_request_type_display() in email_body
            
            # 2. Verificar ID o nombre del remitente
            assert normal_user.get_full_name() in email_body or normal_user.document in email_body
            
            # 3. Verificar fecha y hora del envío
            timestamp_format = flow_request.created_at.strftime("%d/%m/%Y")
            assert timestamp_format in email_body or flow_request.created_at.strftime("%Y-%m-%d") in email_body, \
                f"No se encontró la fecha {timestamp_format} en el cuerpo del correo"
            
            # Verificar formato HTML del correo
            if admin_email.alternatives:
                html_content = next(c for c in admin_email.alternatives if c[1] == 'text/html')[0]
                assert flow_request.get_flow_request_type_display() in html_content
                assert normal_user.get_full_name() in html_content or normal_user.document in html_content
                assert timestamp_format in html_content or flow_request.created_at.strftime("%Y-%m-%d") in html_content


    def test_failure_report_notification_to_admin(self, normal_user, user_lot, user_plot, admin_user, iot_device):
        """
        Verifica que cuando un usuario normal crea un reporte de fallo,
        se notifica al administrador del sistema.
        """
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        # Limpiar bandeja de salida de correos antes de la prueba
        mail.outbox = []
        
        # Crear reporte de fallo
        failure_report = FailureReport.objects.create(
            type='Reporte',
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de prueba para test'
        )
        
        # Verificar que se ha enviado al menos un correo
        assert len(mail.outbox) > 0, "No se envió ningún correo tras crear el reporte"
        
        # Buscar correo dirigido al administrador
        admin_received_email = False
        admin_email = None
        
        for email in mail.outbox:
            if admin_user.email in email.to:
                admin_received_email = True
                admin_email = email
                break
        
        # Verificar que el administrador recibió la notificación
        assert admin_received_email, f"El administrador ({admin_user.email}) no recibió notificación"
        
        # Verificar contenido del correo enviado al administrador
        if admin_email:
            # Verificar que el asunto es claro
            assert "Reporte" in admin_email.subject or "Fallo" in admin_email.subject
            
            # Verificar TODOS los elementos requeridos en el contenido según la HU:
            email_body = admin_email.body
            
            # 1. Verificar el tipo de reporte
            assert failure_report.get_failure_type_display() in email_body
            
            # 2. Verificar ID o nombre del remitente
            assert normal_user.get_full_name() in email_body or normal_user.document in email_body
            
            # 3. Verificar fecha y hora del envío
            timestamp_format = failure_report.created_at.strftime("%d/%m/%Y")
            assert timestamp_format in email_body or failure_report.created_at.strftime("%Y-%m-%d") in email_body, \
                f"No se encontró la fecha {timestamp_format} en el cuerpo del correo"
            
            # Verificar formato HTML del correo
            if admin_email.alternatives:
                html_content = next(c for c in admin_email.alternatives if c[1] == 'text/html')[0]
                assert failure_report.get_failure_type_display() in html_content
                assert normal_user.get_full_name() in html_content or normal_user.document in html_content
                assert timestamp_format in html_content or failure_report.created_at.strftime("%Y-%m-%d") in html_content

    def test_direct_send_flow_request_notification(self, normal_user, user_lot, admin_user, iot_device):
        """
        Prueba directamente la función de envío de notificación para solicitudes,
        verificando que envía el correo correctamente con el formato adecuado.
        """
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        
        # Crear solicitud sin guardar en la base de datos
        flow_request = FlowRequest(
            id=9999,  # ID ficticio para la prueba
            type='Solicitud',
            created_by=normal_user,
            lot=lote1,
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            requested_flow=5.0,
            status='Pendiente',
            observations='Solicitud de prueba directa',
            created_at=timezone.now()
        )
        
        # Llamar directamente a la función de notificación
        result = send_flow_request_created_notification(flow_request)
        
        # Verificar que el envío fue exitoso
        assert result is True, "La función de notificación falló al enviar el correo"
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        
        # Verificar formato del correo enviado
        email = mail.outbox[0]
        
        # Verificar asunto
        assert "Solicitud" in email.subject or "Nueva" in email.subject
        
        # Verificar contenido en texto plano
        email_body = email.body
        assert flow_request.get_flow_request_type_display() in email_body
        assert normal_user.get_full_name() in email_body or normal_user.document in email_body
        timestamp_format = flow_request.created_at.strftime("%d/%m/%Y")
        assert timestamp_format in email_body or flow_request.created_at.strftime("%Y-%m-%d") in email_body
        
        # Verificar contenido HTML
        if email.alternatives:
            html_content = next(c for c in email.alternatives if c[1] == 'text/html')[0]
            assert flow_request.get_flow_request_type_display() in html_content
            assert normal_user.get_full_name() in html_content or normal_user.document in html_content
            assert timestamp_format in html_content or flow_request.created_at.strftime("%Y-%m-%d") in html_content

    def test_direct_send_failure_report_notification(self, normal_user, user_lot, user_plot, iot_device):
        """
        Prueba directamente la función de envío de notificación para reportes,
        verificando que envía el correo correctamente con el formato adecuado.
        """
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        
        # Crear reporte sin guardar en la base de datos
        failure_report = FailureReport(
            id=8888,  # ID ficticio para la prueba
            type='Reporte',
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de prueba directo',
            created_at=timezone.now()
        )
        
        # Llamar directamente a la función de notificación
        result = send_failure_report_created_notification(failure_report)
        
        # Verificar que el envío fue exitoso
        assert result is True, "La función de notificación falló al enviar el correo"
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        
        # Verificar formato del correo enviado
        email = mail.outbox[0]
        
        # Verificar asunto
        assert "Reporte" in email.subject or "Fallo" in email.subject
        
        # Verificar contenido en texto plano
        email_body = email.body
        assert failure_report.get_failure_type_display() in email_body
        assert normal_user.get_full_name() in email_body or normal_user.document in email_body
        timestamp_format = failure_report.created_at.strftime("%d/%m/%Y")
        assert timestamp_format in email_body or failure_report.created_at.strftime("%Y-%m-%d") in email_body
        
        # Verificar contenido HTML
        if email.alternatives:
            html_content = next(c for c in email.alternatives if c[1] == 'text/html')[0]
            assert failure_report.get_failure_type_display() in html_content
            assert normal_user.get_full_name() in html_content or normal_user.document in html_content
            assert timestamp_format in html_content or failure_report.created_at.strftime("%Y-%m-%d") in html_content

    def test_notification_timing_criteria(self, normal_user, user_lot, iot_device):
        """
        Verifica que la notificación se envía en menos de 1 minuto,
        según el criterio de aceptación especificado en el RF67.
        """
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        
        # Registrar tiempo antes de crear la solicitud
        start_time = timezone.now()
        
        # Crear solicitud
        flow_request = FlowRequest.objects.create(
            type='Solicitud',
            created_by=normal_user,
            lot=lote1,
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            requested_flow=5.0,
            status='Pendiente',
            observations='Solicitud de prueba para timing'
        )
        
        # Verificar que hay al menos un correo
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        
        # Registrar tiempo después de verificar el correo
        end_time = timezone.now()
        
        # Calcular tiempo transcurrido en segundos
        elapsed_seconds = (end_time - start_time).total_seconds()
        
        # Verificar que sea menor a 60 segundos (1 minuto según criterio de aceptación del RF67)
        assert elapsed_seconds < 60, f"La notificación tardó {elapsed_seconds} segundos, superando el límite de 60 segundos"