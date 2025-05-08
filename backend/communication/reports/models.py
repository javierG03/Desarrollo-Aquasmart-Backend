from django.db import models
from communication.models import BaseRequestReport
from iot.models import IoTDevice, VALVE_4_ID
from plots_lots.models import Plot
from communication.utils import generate_unique_id

class TypeReport(models.TextChoices):
    WATER_SUPPLY_FAILURE = 'Reporte de Fallo en el Suministro del Agua', 'Reporte de Fallo en el Suministro del Agua'
    APPLICATION_FAILURE = 'Reporte de Fallo en el Aplicativo', 'Reporte de Fallo en el Aplicativo'

class FailureReport(BaseRequestReport):
    """Modelo para almacenar reportes de fallos"""
    id = models.IntegerField(primary_key=True, verbose_name="ID", help_text="Identificador único del reporte de fallo")
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Predio", help_text="Predio al que se le realiza el reporte")
    failure_type = models.CharField(max_length=50, choices=TypeReport.choices, default=TypeReport.WATER_SUPPLY_FAILURE, verbose_name="Tipo de reporte", help_text="Tipo de reporte (suministro de agua o aplicativo)")

    class Meta:
        verbose_name = "Reporte de Fallo"
        verbose_name_plural = "Reportes de Fallo"

    def _validate_plot_is_activate(self):
        ''' Valida que el predio en cuya solicitud está presente, esté habilitado '''
        if self.plot and self.plot.is_activate != True:
            raise ValueError("No se puede realizar un reporte de un predio inhabilitado.")

    def _validate_pending_report_plot_lot(self):
        '''Valida que el predio y el lote no tengan reportes pendientes, excepto si el predio tiene pendiente pero el lote no'''
        # Reportes pendientes para el predio
        plot_pending = FailureReport.objects.filter(plot=self.plot).exclude(status='Finalizado').exclude(pk=self.pk)
        # Reportes pendientes para el lote
        lot_pending = FailureReport.objects.filter(lot=self.lot).exclude(status='Finalizado').exclude(pk=self.pk)

        # Si hay pendiente en el predio pero NO en el lote, se permite
        if plot_pending.exists() and not lot_pending.exists():
            return

        # Si hay pendiente en el lote, o en el predio y el lote, NO se permite
        if lot_pending.exists() or plot_pending.exists():
            raise ValueError("No se puede crear el reporte porque ya existe uno pendiente para el predio o el lote seleccionado.")

    def _assign_plot_from_lot(self):
        ''' Asigna el predio automáticamente desde el lote '''
        if self.lot and hasattr(self.lot, 'plot'):
            self.plot = self.lot.plot

    def clean(self):
        super().clean()
        self._validate_plot_is_activate()
        self._validate_pending_report_plot_lot()

    def save(self, *args, **kwargs):
        self.full_clean()
        # Generar un ID único para el reporte de fallo
        if not self.id:
            self.id = generate_unique_id(FailureReport,"20")

        self.type = 'Reporte'

        super().save(*args, **kwargs)

        self._validate_owner()
        self._assign_plot_from_lot()