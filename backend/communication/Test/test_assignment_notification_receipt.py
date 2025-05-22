import pytest
from django.core import mail
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from communication.assigment_maintenance.models import Assignment, MaintenanceReport
from communication.reports.models import FailureReport, TypeReport


@pytest.mark.django_db
def test_assignment_email_can_be_received(api_client, admin_user, tecnico_user, normal_user,
                                          user_lot, user_plot, iot_device, login_and_validate_otp,
                                          settings):
    """
    ✅ Verifica que el correo de notificación pueda ser recibido tras una asignación.
    """

    # 🔧 Forzar backend de correo en memoria
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    # 🔐 Login como administrador
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    

    # 🔐 Asignar permisos
    content_type = ContentType.objects.get_for_model(Assignment)
    assign_perm = Permission.objects.get_or_create(codename="can_assign_user", content_type=content_type)[0]
    admin_user.user_permissions.add(assign_perm)

    be_assigned_perm = Permission.objects.get_or_create(codename="can_be_assigned", content_type=content_type)[0]
    tecnico_user.user_permissions.add(be_assigned_perm)
    tecnico_user.save()

    # 📄 Crear reporte
    
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse('water-supply-failure-create')
    # Crear una solicitud de caudal
    response = client.post(
        url,
        {
            "observations": "Esto es un reporte de fallo en el suministro de agua",
            "status": "En Proceso",
            "type": "Reporte",
            "failure_type":"Fallo en el Suministro del Agua",
            "lot": user_lot[0].pk,
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó la solicitud de caudal correctamente"
    )
    print ("✅La solicitud de caudal se guardó correctamente")
    failure_report = FailureReport.objects.get(id=response.data["id"])
    

    # Asifnar el reporte de mantenimiento a un usuario
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('assignment-create')
    
    mail.outbox = []
    
    response = client.post(
        url, data=
        {
            "failure_report": failure_report.pk,
            "assigned_to": tecnico_user.document,
            "status": "Asignado",
            "observations": "Esto es una asignación de prueba",
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó la asignación de mantenimiento correctamente"
    )

    assert len(mail.outbox) > 0, "❌ No se envió ningún correo de notificación."
    

    print("Admin ID:", admin_user.pk, admin_user.email)
    print("Técnico ID:", tecnico_user.pk, tecnico_user.email)

    email = mail.outbox[0]
    print(f"De: {email.from_email}")
    print(f"Asunto: {email.subject}")
    print(f"Para: {email.to}")
    print(f"Cuerpo: {email.body}")

    assert any(admin_user.email in email.to for email in mail.outbox)

    tecnico_received_mail = False

    for email in mail.outbox:
        if tecnico_user.email in email.to:
            tecnico_received_mail = True
            break
        
    assert tecnico_received_mail, "No se envió correo al tecnico"

    

    assert tecnico_user.email in mail.outbox[0].to, f"❌ El destinatario {tecnico_user.email} no está en la lista de correos: {mail.outbox[0].to}"

    
    assert "asignación" in email.subject.lower(), "❌ El asunto del correo no menciona 'asignación'."
    assert tecnico_user.email in email.to, f"❌ El destinatario {tecnico_user.email} no está en la lista de correos."

    print("✅ El correo de asignación fue recibido correctamente.")
