from django.utils import timezone
from django.db import models
from users.models import CustomUser
from plots_lots.models import Lot, Plot
from iot.models import IoTDevice, VALVE_4_ID

class FlowChangeRequest(models.Model):
    """Modelo para almacenar las solicitudes de cambio de caudal."""

    REQUEST_STATUS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Solicitante", help_text="Usuario que realiza la solicitud de cambio de caudal")
    device = models.ForeignKey(IoTDevice, on_delete=models.CASCADE, verbose_name="Dispositivo", help_text="Dispositivo IoT (válvula) asociado a la solicitud")
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Lote", help_text="Lote al que se le solicita el cambio de caudal")
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Predio", help_text="Predio de la válvula principal (si es válvula principal de predio)")
    requested_flow = models.FloatField(verbose_name="Caudal solicitado (L/s)", help_text="Valor del caudal solicitado en litros por segundo")
    status = models.CharField(max_length=10, choices=REQUEST_STATUS, default='pendiente', verbose_name="Estado", help_text="Estado actual de la solicitud")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha solicitud", help_text="Fecha y hora en que se creó la solicitud")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha revisión", help_text="Fecha y hora en que la solicitud fue revisada (aprobada o rechazada)")

    class Meta:
        verbose_name = "Solicitud de cambio de caudal"
        verbose_name_plural = "Solicitudes de cambio de caudal"

    def __str__(self):
        return f"Solicitud de {self.user.get_full_name()} para {self.lot} ({self.requested_flow} L/s) - {self.status}"

    def clean(self):
        # Validar que el lote tenga un dispositivo IoT de tipo válvula 4"
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if not device:
            raise ValueError("El lote no tiene una válvula 4\" asociada.")
        # Validar caudal igual al actual
        if self.requested_flow is not None and device.actual_flow == self.requested_flow:
            raise ValueError("Ya tienes un caudal activo con ese valor. Debes solicitar un valor diferente.")

    def save(self, *args, **kwargs):
        # Asignar plot y device automáticamente desde el lote
        if self.lot:
            self.plot = self.lot.plot
            # Buscar el dispositivo IoT de tipo válvula 4" asociado al lote
            device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
            if not device:
                raise ValueError("El lote no tiene una válvula 4\" asociada.")
            self.device = device

        # Detectar si es una actualización (ya existe en BD)
        if self.pk:
            old = FlowChangeRequest.objects.get(pk=self.pk)
            # Si el status cambia de 'pendiente' a 'aprobada' o 'rechazada'
            if old.status == 'pendiente' and self.status in ['aprobada', 'rechazada']:
                self.reviewed_at = timezone.now()
                # Actualizar el caudal actual del dispositivo si el status es 'aprobada'
                if self.status == 'aprobada':
                    self.device.actual_flow = self.requested_flow
                    self.device.save()
            # Si ya fue revisada, no permitir cambiar el status nuevamente
            elif old.status in ['aprobada', 'rechazada'] and self.status != old.status:
                raise ValueError("No se puede cambiar el estado una vez que la solicitud ha sido revisada.")
        else:
            # Si es nueva, asegurarse que reviewed_at esté vacío
            if self.status == 'pendiente':
                self.reviewed_at = None
            elif self.status in ['aprobada', 'rechazada']:
                self.reviewed_at = timezone.now()
                if self.status == 'aprobada':
                    self.device.actual_flow = self.requested_flow
                    self.device.save()
        super().save(*args, **kwargs)