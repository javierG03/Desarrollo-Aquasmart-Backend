from django.db import models
from communication.models import BaseRequestReport
from iot.models import IoTDevice, VALVE_4_ID
from plots_lots.models import Plot


class TypeReport(models.TextChoices):
    WATER_SUPPLY_FAILURE = 'Reporte de Fallo en el Suministro del Agua', 'Reporte de Fallo en el Suministro del Agua'
    APPLICATION_FAILURE = 'Reporte de Fallo en el Aplicativo', 'Reporte de Fallo en el Aplicativo'

class FailureReport(BaseRequestReport):
    """Modelo para almacenar reportes de fallos"""
    id = models.IntegerField(primary_key=True, verbose_name="ID", help_text="Identificador único del reporte de fallo")
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Predio", help_text="Predio al que se le realiza el reporte")
    failure_type = models.CharField(max_length=50, choices=TypeReport.choices, default=TypeReport.WATER_SUPPLY_FAILURE, verbose_name="Tipo de reporte", help_text="Tipo de reporte (suministro de agua o aplicativo)")

    def _validate_owner(self):
        ''' Valida que el usuario solicitante sea dueño del predio '''
        self._validate_owner()
        if self.plot:
            if self.created_by != self.plot.owner:
                raise ValueError("Solo el dueño del predio puede realizar una solicitud para el caudal de este lote.")

    def _validate_plot_is_activate(self):
        ''' Valida que el predio en cuya solicitud está presente, esté habilitado '''
        if self.plot and self.plot.is_activate != True:
            raise ValueError("No se puede realizar un reporte de un predio inhabilitado.")

    def _assign_plot_from_lot(self):
        ''' Asigna el predio automáticamente desde el lote '''
        if self.lot and hasattr(self.lot, 'plot'):
            self.plot = self.lot.plot