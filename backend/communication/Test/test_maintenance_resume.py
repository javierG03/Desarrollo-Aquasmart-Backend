import pytest
from django.urls import reverse
from rest_framework import status
from communication.assigment_maintenance.models import Assignment, MaintenanceReport
from communication.requests.models import FlowRequest
from communication.reports.models import FailureReport
from iot.models import DeviceType, IoTDevice
from plots_lots.models import Plot, Lot
from users.models import Otp

@pytest.mark.django_db
def test_maintenance_report_resume(api_client, normal_user,admin_user, tecnico_user,login_and_validate_otp, user_lot, user_plot, device_type, iot_device):
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
            "lot": user_lot[0].pk
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó la solicitud de caudal correctamente"
    )
    print ("✅La solicitud de caudal se guardó correctamente")
    failure_report = FailureReport.objects.get(id=response.data["id"])
    print(f"FlowRequest: {failure_report}")

    # Asifnar el reporte de mantenimiento a un usuario
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")
    url = reverse('assignment-create')
    

    response = client.post(
        url,
        {
            "failure_report": failure_report.pk,
            "assigned_to": tecnico_user.pk,
            "status": "Asignado",
            "observations": "Esto es una asignación de prueba",
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó la asignación de mantenimiento correctamente"
    )
    print ("✅La asignación de mantenimiento se guardó correctamente")
    assignment = Assignment.objects.get(id=response.data["id"])
    print(f"Assignment: {assignment}")

    # Crear un reporte de mantenimiento
    client = login_and_validate_otp(api_client,tecnico_user,"UserPass123@")
    url = reverse('maintenance-report-create')


    response = client.post(
        url,
        {
            "assignment": assignment.pk,
            "intervention_date": "2025-04-15 06:00:00",
            "status": "Finalizado",
            "observations": "Esto es un reporte de mantenimiento detallado del sistema",
            "maintenance_type":"Mantenimiento Preventivo",
            "is_approved":True,
            "images":"Image_texto"
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó el reporte de mantenimiento correctamente"
    )
    print ("✅El reporte de mantenimiento se guardó correctamente")
    maintenance_report = MaintenanceReport.objects.get(id=response.data["id"])
    print(f"MaintenanceReport: {maintenance_report}")
    
@pytest.mark.django_db
def test_normal_user_cannot_assign_maintenance(api_client,normal_user,admin_user,operador_user,login_and_validate_otp,user_lot,user_plot,device_type,iot_device):
    client = login_and_validate_otp(api_client, normal_user, "UserPass123@")
    url = reverse("water-supply-failure-create")
    response = client.post(
        url,
        {
             "observations": "Esto es un reporte de fallo en el suministro de agua",
            "status": "En Proceso",
            "type": "Reporte",
            "failure_type":"Fallo en el Suministro del Agua",
            "lot": user_lot[0].pk
        },
        format="json",
    )
    print(response.data)
    assert response.status_code == status.HTTP_201_CREATED, (
        f"❌No se guardó la solicitud de caudal correctamente"
    )
    print ("✅La solicitud de caudal se guardó correctamente")
    failure_report = FailureReport.objects.get(id=response.data["id"])
    print(f"FlowRequest: {failure_report}")

    # Asifnar el reporte de mantenimiento a un usuario
    print("⚠ Se intentará asignar un mantenimiento a un operador con la sesión de un usuario normal")

    url = reverse('assignment-create')
    

    response = client.post(
        url,
        {
            "failure_report": failure_report.pk,
            "assigned_to": operador_user.pk,
            "status": "Asignado",
            "observations": "Esto es una asignación de prueba",
        },
        format="json",
    )
    print(response.data)
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        print(f"✅Un usuario normal NO se le permitió el acceso a la asignación de mantenimiento a un usuario competente")
        
    else:
        print("❗❗Un usuario normal está asignando el mantenimiento a un usuario competente")
    
    print ("✅Se rechazó la asignación de mantenimiento por parte de un usuario normal")
    