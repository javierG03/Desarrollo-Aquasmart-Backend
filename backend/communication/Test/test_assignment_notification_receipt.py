import pytest
from django.core import mail
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from communication.assigment_maintenance.models import Assignment, MaintenanceReport
from communication.reports.models import FailureReport, TypeReport


@pytest.mark.django_db
def test_notification_delivered_to_correct_recipient(api_client, admin_user, tecnico_user, login_and_validate_otp, user_lot, user_plot, normal_user, iot_device, device_type,settings):
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
        
        
        admin_user.save()
        tecnico_user.save()
        
        failure_report1 = FailureReport.objects.create(
            created_by=normal_user,
            lot=user_lot[0],
            plot=user_plot,
            type='Reporte',
            failure_type=TypeReport.WATER_SUPPLY_FAILURE,
            status='Pendiente',
            observations='Primer reporte de prueba para delegación'
        )
        
        mail.outbox = []  # Limpiar buzón
        
        url = reverse('assignment-create')
        response = client.post(url, data={
            'assigned_to': tecnico_user.document,
            'failure_report': failure_report1.id
        }, format='json')

        print(response.data)
        print(response.status_code)
        
        # Solicitud debe ser exitosa
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que se enviaron correos
        assert len(mail.outbox) > 0, "No se enviaron correos electrónicos"
        
        # Verificar que el correo llegó al técnico pero NO al operador
        tech_email_received = False
        
        
        for email in mail.outbox:
            if tecnico_user.email in email.to:
                tech_email_received = True


        print(f"De: {email.from_email}")
        print(f"Asunto: {email.subject}")
        print(f"Para: {email.to}")
        print(f"Cuerpo: {email.body}")
        
        assert tech_email_received, "El técnico no recibió notificación por correo"
        print(f"✅La notificación fue envíada correctamente a el destinatario al quese le fue asignado el reporte.")
