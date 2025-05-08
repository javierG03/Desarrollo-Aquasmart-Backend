from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def _send_notification_email(subject, context, template_name, recipient_email):
    """
    Función helper para enviar correos electrónicos con plantillas
    """
    message_text = render_to_string(f'emails/{template_name}.txt', context)
    message_html = render_to_string(f'emails/{template_name}.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=strip_tags(message_text),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email],
            fail_silently=False,
            html_message=message_html
        )
        return True
    except Exception as e:
        print(f"Error al enviar notificación: {e}")
        return False

def send_failure_report_created_notification(report):
    """
    Envía notificación cuando se crea un nuevo reporte de fallo
    """
    subject = "✅ Nuevo Reporte de Fallo Creado"
    
    context = {
        'report_id': report.id,
        'failure_type': report.get_failure_type_display(),
        'created_at': report.created_at,
        'plot_name': report.plot.name if report.plot else "No especificado",
        'lot_name': report.lot.name if report.lot else "No especificado",
        'observations': report.observations or "Sin observaciones",
        'status': report.get_status_display(),
        'user_name': report.created_by.get_full_name(),
    }
    
    return _send_notification_email(subject, context, 'failure_report_created', report.created_by.email)

def send_failure_report_status_notification(report):
    """
    Envía notificación cuando cambia el estado de un reporte de fallo
    """
    subject = f"🔄 Actualización de Estado - Reporte #{report.id}"
    
    context = {
        'report_id': report.id,
        'failure_type': report.get_failure_type_display(),
        'status': report.get_status_display(),
        'plot_name': report.plot.name if report.plot else "No especificado",
        'lot_name': report.lot.name if report.lot else "No especificado",
        'finalized_at': report.finalized_at if report.finalized_at else "No finalizado",
        'observations': report.observations or "Sin observaciones",
        'user_name': report.created_by.get_full_name(),
    }
    
    return _send_notification_email(subject, context, 'failure_report_status', report.created_by.email)

def send_flow_request_created_notification(request):
    """
    Envía notificación cuando se crea una nueva solicitud de caudal
    """
    subject = "✅ Nueva Solicitud de Caudal Creada"
    
    context = {
        'request_id': request.id,
        'request_type': request.get_flow_request_type_display(),
        'requested_flow': request.requested_flow or "No aplica",
        'created_at': request.created_at,
        'lot_name': request.lot.name if request.lot else "No especificado",
        'observations': request.observations or "Sin observaciones",
        'status': request.get_status_display(),
        'user_name': request.created_by.get_full_name(),
    }
    
    return _send_notification_email(subject, context, 'flow_request_created', request.created_by.email)

def send_flow_request_decision_notification(request):
    """
    Envía notificación cuando se aprueba/rechaza una solicitud de caudal
    """
    if request.is_approved:
        subject = f"✅ Solicitud #{request.id} Aprobada"
        status_text = "APROBADA"
    else:
        subject = f"❌ Solicitud #{request.id} Rechazada"
        status_text = "RECHAZADA"
    
    context = {
        'request_id': request.id,
        'request_type': request.get_flow_request_type_display(),
        'status_text': status_text,
        'requested_flow': request.requested_flow or "No aplica",
        'lot_name': request.lot.name if request.lot else "No especificado",
        'finalized_at': request.finalized_at if request.finalized_at else "No finalizado",
        'observations': request.observations or "Sin observaciones",
        'user_name': request.created_by.get_full_name(),
    }
    
    return _send_notification_email(subject, context, 'flow_request_decision', request.created_by.email)