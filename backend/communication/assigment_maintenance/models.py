from django.db import models
from django.conf import settings
from communication.requests.models import FlowRequest
from communication.reports.models import FailureReport


class Assignment(models.Model):
    """Modelo para almacenar asignaciones de solicitudes y reportes de fallos"""
    # Implementar la lógica del ID
    id = models.IntegerField(primary_key=True, verbose_name="ID", help_text="Identificador único de la asignación")
    flow_request = models.ForeignKey(FlowRequest, null=True, blank=True, on_delete=models.CASCADE, verbose_name="Solicitud de caudal", help_text="Solicitud de caudal asociada a la asignación")
    failure_report = models.ForeignKey(FailureReport, null=True, blank=True, on_delete=models.CASCADE, verbose_name="Reporte de fallo", help_text="Reporte de fallo asociado a la asignación")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments_made', verbose_name="Usuario que asigna", help_text="Usuario que realiza la asignación")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments_received', verbose_name="Usuario a asignar", help_text="Usuario al que se le asigna la solicitud/reporte")
    assignment_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de asignación", help_text="Fecha y hora en que se realizó la asignación")
    reassigned = models.BooleanField(default=False, verbose_name="Fue reasignado", help_text="Indica si la solicitud/reporte ha sido reasignada")

    class Meta:
        verbose_name = "Asignación de solicitud/reporte"
        verbose_name_plural = "Asignaciones de solicitudes/reportes"

    def __str__(self):
        return f"Asignación de {self.assigned_by} a {self.assigned_to} ({self.assignment_date})"


class MaintenanceReport(models.Model):
    """Modelo para almacenar informes de mantenimiento"""
    # Implementar la lógica del ID
    id = models.IntegerField(primary_key=True, verbose_name="ID", help_text="Identificador único del informe de mantenimiento")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, verbose_name="Asignación", help_text="Asignación asociada al informe de mantenimiento")
    intervention_date = models.DateTimeField(verbose_name="Fecha de intervención", help_text="Fecha y hora en que se realizó la intervención")
    images = models.TextField(null=True, blank=True, verbose_name="Imágenes", help_text="Imágenes de la intervención realizada")
    description = models.CharField(null=True, blank=True, max_length=1000, verbose_name="Descripción", help_text="Descripción de la intervención realizada")
    status = models.CharField(max_length=50, choices=[('Finalizado', 'Finalizado'), ('Requiere nueva intervención', 'Requiere nueva intervención')], verbose_name="Estado", help_text="Estado final del informe de mantenimiento")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación", help_text="Fecha y hora en que se creó el informe de mantenimiento")
    is_approved = models.BooleanField(default=False, verbose_name="Fue aprobado", help_text="Indica si el informe de mantenimiento fue aprobado o no")

    class Meta:
        verbose_name = "Informe de mantenimiento"
        verbose_name_plural = "Informes de mantenimiento"

    def __str__(self):
        return f"Informe de mantenimiento de {self.assignment.assigned_to} ({self.intervention_date})"