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
        print("\n=== PRUEBA NOTIFICACIÓN DE SOLICITUD DE CAUDAL AL ADMINISTRADOR ===")
        
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        print(f"Usuario creador: {normal_user.get_full_name()} (documento: {normal_user.document})")
        print(f"Administrador destinatario: {admin_user.get_full_name()} (email: {admin_user.email})")
        print(f"Lote seleccionado: {lote1.id_lot}")
        
        # Limpiar bandeja de salida de correos antes de la prueba
        mail.outbox = []
        print("Bandeja de correos limpiada")
        
        # Crear solicitud de cambio de caudal
        print("Creando solicitud de cambio de caudal...")
        flow_request = FlowRequest.objects.create(
            type='Solicitud',
            created_by=normal_user,
            lot=lote1,  # Este lote ya tiene la válvula 4" asociada
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            requested_flow=5.0,
            status='Pendiente',
            observations='Solicitud de prueba para test'
        )
        print(f"Solicitud creada: ID={flow_request.id}, Tipo={flow_request.get_flow_request_type_display()}")
        
        # Verificar que se ha enviado al menos un correo
        print(f"Verificando correos enviados... ({len(mail.outbox)} encontrados)")
        assert len(mail.outbox) > 0, "No se envió ningún correo tras crear la solicitud"
        print(f"✅ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Buscar correo dirigido al administrador
        admin_received_email = False
        admin_email = None
        
        print("Buscando correo dirigido al administrador...")
        for i, email in enumerate(mail.outbox):
            print(f"  Correo #{i+1}: Para={email.to}, Asunto={email.subject}")
            if admin_user.email in email.to:
                admin_received_email = True
                admin_email = email
                print(f"  ✅ Correo dirigido al administrador encontrado")
                break
        
        # Verificar que el administrador recibió la notificación
        assert admin_received_email, f"El administrador ({admin_user.email}) no recibió notificación"
        print("✅ El administrador recibió la notificación correctamente")
        
        # Verificar contenido del correo enviado al administrador
        if admin_email:
            print("\nAnalizando contenido del correo al administrador:")
            
            # Verificar que el asunto es claro
            print(f"  Asunto: {admin_email.subject}")
            assert "Solicitud" in admin_email.subject or "Nueva" in admin_email.subject
            print("  ✅ Asunto contiene 'Solicitud' o 'Nueva'")
            
            # Verificar TODOS los elementos requeridos en el contenido según la HU:
            email_body = admin_email.body
            print(f"  Fragmento del cuerpo del correo: {email_body[:200]}...")
            
            # 1. Verificar el tipo de solicitud
            print(f"  Buscando tipo de solicitud: '{flow_request.get_flow_request_type_display()}'")
            assert flow_request.get_flow_request_type_display() in email_body
            print("  ✅ Tipo de solicitud encontrado en el cuerpo")
            
            # 2. Verificar ID o nombre del remitente
            print(f"  Buscando nombre del remitente: '{normal_user.get_full_name()}'")
            assert normal_user.get_full_name() in email_body or normal_user.document in email_body
            print("  ✅ Nombre o documento del remitente encontrado")
            
            # 3. Verificar fecha y hora del envío
            timestamp_format = flow_request.created_at.strftime("%d/%m/%Y")
            alt_timestamp = flow_request.created_at.strftime("%Y-%m-%d")
            print(f"  Buscando fecha de envío: '{timestamp_format}' o '{alt_timestamp}'")
            assert timestamp_format in email_body or alt_timestamp in email_body, \
                f"No se encontró la fecha {timestamp_format} en el cuerpo del correo"
            print("  ✅ Fecha de envío encontrada en el cuerpo")
            
            # Verificar formato HTML del correo
            if admin_email.alternatives:
                print("\n  Analizando contenido HTML del correo:")
                html_content = next(c for c in admin_email.alternatives if c[1] == 'text/html')[0]
                html_snippet = html_content[:200].replace('\n', ' ')
                print(f"  Fragmento del HTML: {html_snippet}...")
                
                assert flow_request.get_flow_request_type_display() in html_content
                print("  ✅ Tipo de solicitud encontrado en el HTML")
                
                assert normal_user.get_full_name() in html_content or normal_user.document in html_content
                print("  ✅ Nombre o documento del remitente encontrado en el HTML")
                
                assert timestamp_format in html_content or alt_timestamp in html_content
                print("  ✅ Fecha de envío encontrada en el HTML")
            else:
                print("  ⚠️ El correo no tiene contenido HTML alternativo")


    def test_failure_report_notification_to_admin(self, normal_user, user_lot, user_plot, admin_user, iot_device):
        """
        Verifica que cuando un usuario normal crea un reporte de fallo,
        se notifica al administrador del sistema.
        """
        print("\n=== PRUEBA NOTIFICACIÓN DE REPORTE DE FALLO AL ADMINISTRADOR ===")
        
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        print(f"Usuario creador: {normal_user.get_full_name()} (documento: {normal_user.document})")
        print(f"Administrador destinatario: {admin_user.get_full_name()} (email: {admin_user.email})")
        print(f"Lote seleccionado: {lote1.id_lot}, Predio: {user_plot.plot_name}")
        
        # Limpiar bandeja de salida de correos antes de la prueba
        mail.outbox = []
        print("Bandeja de correos limpiada")
        
        # Crear reporte de fallo
        print("Creando reporte de fallo...")
        failure_report = FailureReport.objects.create(
            type='Reporte',
            created_by=normal_user,
            lot=lote1,
            plot=user_plot,
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Reporte de prueba para test'
        )
        print(f"Reporte creado: ID={failure_report.id}, Tipo={failure_report.get_failure_type_display()}")
        
        # Verificar que se ha enviado al menos un correo
        print(f"Verificando correos enviados... ({len(mail.outbox)} encontrados)")
        assert len(mail.outbox) > 0, "No se envió ningún correo tras crear el reporte"
        print(f"✅ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Buscar correo dirigido al administrador
        admin_received_email = False
        admin_email = None
        
        print("Buscando correo dirigido al administrador...")
        for i, email in enumerate(mail.outbox):
            print(f"  Correo #{i+1}: Para={email.to}, Asunto={email.subject}")
            if admin_user.email in email.to:
                admin_received_email = True
                admin_email = email
                print(f"  ✅ Correo dirigido al administrador encontrado")
                break
        
        # Verificar que el administrador recibió la notificación
        assert admin_received_email, f"El administrador ({admin_user.email}) no recibió notificación"
        print("✅ El administrador recibió la notificación correctamente")
        
        # Verificar contenido del correo enviado al administrador
        if admin_email:
            print("\nAnalizando contenido del correo al administrador:")
            
            # Verificar que el asunto es claro
            print(f"  Asunto: {admin_email.subject}")
            assert "Reporte" in admin_email.subject or "Fallo" in admin_email.subject
            print("  ✅ Asunto contiene 'Reporte' o 'Fallo'")
            
            # Verificar TODOS los elementos requeridos en el contenido según la HU:
            email_body = admin_email.body
            print(f"  Fragmento del cuerpo del correo: {email_body[:200]}...")
            
            # 1. Verificar el tipo de reporte
            print(f"  Buscando tipo de reporte: '{failure_report.get_failure_type_display()}'")
            assert failure_report.get_failure_type_display() in email_body
            print("  ✅ Tipo de reporte encontrado en el cuerpo")
            
            # 2. Verificar ID o nombre del remitente
            print(f"  Buscando nombre del remitente: '{normal_user.get_full_name()}'")
            assert normal_user.get_full_name() in email_body or normal_user.document in email_body
            print("  ✅ Nombre o documento del remitente encontrado")
            
            # 3. Verificar fecha y hora del envío
            timestamp_format = failure_report.created_at.strftime("%d/%m/%Y")
            alt_timestamp = failure_report.created_at.strftime("%Y-%m-%d")
            print(f"  Buscando fecha de envío: '{timestamp_format}' o '{alt_timestamp}'")
            assert timestamp_format in email_body or alt_timestamp in email_body, \
                f"No se encontró la fecha {timestamp_format} en el cuerpo del correo"
            print("  ✅ Fecha de envío encontrada en el cuerpo")
            
            # Verificar formato HTML del correo
            if admin_email.alternatives:
                print("\n  Analizando contenido HTML del correo:")
                html_content = next(c for c in admin_email.alternatives if c[1] == 'text/html')[0]
                html_snippet = html_content[:200].replace('\n', ' ')
                print(f"  Fragmento del HTML: {html_snippet}...")
                
                assert failure_report.get_failure_type_display() in html_content
                print("  ✅ Tipo de reporte encontrado en el HTML")
                
                assert normal_user.get_full_name() in html_content or normal_user.document in html_content
                print("  ✅ Nombre o documento del remitente encontrado en el HTML")
                
                assert timestamp_format in html_content or alt_timestamp in html_content
                print("  ✅ Fecha de envío encontrada en el HTML")
            else:
                print("  ⚠️ El correo no tiene contenido HTML alternativo")

    def test_direct_send_flow_request_notification(self, normal_user, user_lot, admin_user, iot_device):
        """
        Prueba directamente la función de envío de notificación para solicitudes,
        verificando que envía el correo correctamente con el formato adecuado.
        """
        print("\n=== PRUEBA DIRECTA DE LA FUNCIÓN DE NOTIFICACIÓN PARA SOLICITUDES ===")
        
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        print(f"Usuario creador: {normal_user.get_full_name()}")
        print(f"Lote seleccionado: {lote1.id_lot}")
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        print("Bandeja de correos limpiada")
        
        # Crear solicitud sin guardar en la base de datos
        print("Creando objeto solicitud (sin guardar en la base de datos)...")
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
        print(f"Solicitud creada: ID={flow_request.id}, Tipo={flow_request.get_flow_request_type_display()}")
        
        # Llamar directamente a la función de notificación
        print("Llamando directamente a la función de notificación...")
        result = send_flow_request_created_notification(flow_request)
        
        # Verificar que el envío fue exitoso
        assert result is True, "La función de notificación falló al enviar el correo"
        print("✅ La función de notificación retornó True (éxito)")
        
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        print(f"✅ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Verificar formato del correo enviado
        email = mail.outbox[0]
        print(f"Analizando primer correo enviado a: {email.to}")
        
        # Verificar asunto
        print(f"Asunto: {email.subject}")
        assert "Solicitud" in email.subject or "Nueva" in email.subject
        print("✅ Asunto contiene 'Solicitud' o 'Nueva'")
        
        # Verificar contenido en texto plano
        email_body = email.body
        print(f"Fragmento del cuerpo: {email_body[:200]}...")
        
        print(f"Buscando tipo de solicitud: '{flow_request.get_flow_request_type_display()}'")
        assert flow_request.get_flow_request_type_display() in email_body
        print("✅ Tipo de solicitud encontrado en el cuerpo")
        
        print(f"Buscando nombre del remitente: '{normal_user.get_full_name()}'")
        assert normal_user.get_full_name() in email_body or normal_user.document in email_body
        print("✅ Nombre o documento del remitente encontrado en el cuerpo")
        
        timestamp_format = flow_request.created_at.strftime("%d/%m/%Y")
        alt_timestamp = flow_request.created_at.strftime("%Y-%m-%d")
        print(f"Buscando fecha: '{timestamp_format}' o '{alt_timestamp}'")
        assert timestamp_format in email_body or alt_timestamp in email_body
        print("✅ Fecha encontrada en el cuerpo")
        
        # Verificar contenido HTML
        if email.alternatives:
            print("\nAnalizando contenido HTML del correo:")
            html_content = next(c for c in email.alternatives if c[1] == 'text/html')[0]
            html_snippet = html_content[:200].replace('\n', ' ')
            print(f"Fragmento del HTML: {html_snippet}...")
            
            assert flow_request.get_flow_request_type_display() in html_content
            print("✅ Tipo de solicitud encontrado en el HTML")
            
            assert normal_user.get_full_name() in html_content or normal_user.document in html_content
            print("✅ Nombre del remitente encontrado en el HTML")
            
            assert timestamp_format in html_content or alt_timestamp in html_content
            print("✅ Fecha encontrada en el HTML")
        else:
            print("⚠️ El correo no tiene contenido HTML alternativo")

    def test_direct_send_failure_report_notification(self, normal_user, user_lot, user_plot, iot_device):
        """
        Prueba directamente la función de envío de notificación para reportes,
        verificando que envía el correo correctamente con el formato adecuado.
        """
        print("\n=== PRUEBA DIRECTA DE LA FUNCIÓN DE NOTIFICACIÓN PARA REPORTES ===")
        
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        print(f"Usuario creador: {normal_user.get_full_name()}")
        print(f"Lote seleccionado: {lote1.id_lot}, Predio: {user_plot.plot_name}")
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        print("Bandeja de correos limpiada")
        
        # Crear reporte sin guardar en la base de datos
        print("Creando objeto reporte (sin guardar en la base de datos)...")
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
        print(f"Reporte creado: ID={failure_report.id}, Tipo={failure_report.get_failure_type_display()}")
        
        # Llamar directamente a la función de notificación
        print("Llamando directamente a la función de notificación...")
        result = send_failure_report_created_notification(failure_report)
        
        # Verificar que el envío fue exitoso
        assert result is True, "La función de notificación falló al enviar el correo"
        print("✅ La función de notificación retornó True (éxito)")
        
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        print(f"✅ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Verificar formato del correo enviado
        email = mail.outbox[0]
        print(f"Analizando primer correo enviado a: {email.to}")
        
        # Verificar asunto
        print(f"Asunto: {email.subject}")
        assert "Reporte" in email.subject or "Fallo" in email.subject
        print("✅ Asunto contiene 'Reporte' o 'Fallo'")
        
        # Verificar contenido en texto plano
        email_body = email.body
        print(f"Fragmento del cuerpo: {email_body[:200]}...")
        
        print(f"Buscando tipo de reporte: '{failure_report.get_failure_type_display()}'")
        assert failure_report.get_failure_type_display() in email_body
        print("✅ Tipo de reporte encontrado en el cuerpo")
        
        print(f"Buscando nombre del remitente: '{normal_user.get_full_name()}'")
        assert normal_user.get_full_name() in email_body or normal_user.document in email_body
        print("✅ Nombre o documento del remitente encontrado en el cuerpo")
        
        timestamp_format = failure_report.created_at.strftime("%d/%m/%Y")
        alt_timestamp = failure_report.created_at.strftime("%Y-%m-%d")
        print(f"Buscando fecha: '{timestamp_format}' o '{alt_timestamp}'")
        assert timestamp_format in email_body or alt_timestamp in email_body
        print("✅ Fecha encontrada en el cuerpo")
        
        # Verificar contenido HTML
        if email.alternatives:
            print("\nAnalizando contenido HTML del correo:")
            html_content = next(c for c in email.alternatives if c[1] == 'text/html')[0]
            html_snippet = html_content[:200].replace('\n', ' ')
            print(f"Fragmento del HTML: {html_snippet}...")
            
            assert failure_report.get_failure_type_display() in html_content
            print("✅ Tipo de reporte encontrado en el HTML")
            
            assert normal_user.get_full_name() in html_content or normal_user.document in html_content
            print("✅ Nombre del remitente encontrado en el HTML")
            
            assert timestamp_format in html_content or alt_timestamp in html_content
            print("✅ Fecha encontrada en el HTML")
        else:
            print("⚠️ El correo no tiene contenido HTML alternativo")

    def test_notification_timing_criteria(self, normal_user, user_lot, iot_device):
        """
        Verifica que la notificación se envía en menos de 1 minuto,
        según el criterio de aceptación especificado en el RF67.
        """
        print("\n=== PRUEBA DE TIEMPO DE ENTREGA DE NOTIFICACIONES ===")
        
        lote1, _, _ = user_lot
        valvula4, _, _, _ = iot_device  # Tomamos la válvula 4" asociada al lote
        
        print(f"Usuario creador: {normal_user.get_full_name()}")
        print(f"Lote seleccionado: {lote1.id_lot}")
        
        # Limpiar bandeja de salida de correos
        mail.outbox = []
        print("Bandeja de correos limpiada")
        
        # Registrar tiempo antes de crear la solicitud
        start_time = timezone.now()
        print(f"Tiempo inicial: {start_time.strftime('%H:%M:%S.%f')}")
        
        # Crear solicitud
        print("Creando solicitud de cambio de caudal y esperando notificación...")
        flow_request = FlowRequest.objects.create(
            type='Solicitud',
            created_by=normal_user,
            lot=lote1,
            flow_request_type=FlowRequestType.FLOW_CHANGE,
            requested_flow=5.0,
            status='Pendiente',
            observations='Solicitud de prueba para timing'
        )
        print(f"Solicitud creada: ID={flow_request.id}")
        
        # Verificar que hay al menos un correo
        assert len(mail.outbox) > 0, "No se envió ningún correo"
        print(f"✅ Se enviaron {len(mail.outbox)} correos electrónicos")
        
        # Registrar tiempo después de verificar el correo
        end_time = timezone.now()
        print(f"Tiempo final: {end_time.strftime('%H:%M:%S.%f')}")
        
        # Calcular tiempo transcurrido en segundos
        elapsed_seconds = (end_time - start_time).total_seconds()
        print(f"Tiempo transcurrido: {elapsed_seconds:.6f} segundos")
        
        # Verificar que sea menor a 60 segundos (1 minuto según criterio de aceptación del RF67)
        assert elapsed_seconds < 60, f"La notificación tardó {elapsed_seconds} segundos, superando el límite de 60 segundos"
        print(f"✅ La notificación se envió en menos de 60 segundos ({elapsed_seconds:.6f}s)")