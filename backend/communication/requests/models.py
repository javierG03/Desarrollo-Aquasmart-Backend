from django.db import models
from communication.models import BaseRequestReport
from iot.models import IoTDevice, VALVE_4_ID
from functools import cached_property


class FlowRequestType(models.TextChoices):
    FLOW_CHANGE = 'Solicitud de Cambio de Caudal', 'Solicitud de Cambio de Caudal'
    FLOW_TEMPORARY_CANCEL = 'Solicitud de Cancelación Temporal de Caudal', 'Solicitud de Cancelación Temporal de Caudal'
    FLOW_DEFINITIVE_CANCEL = 'Solicitud de Cancelación Definitiva de Caudal', 'Solicitud de Cancelación Definitiva de Caudal'
    FLOW_ACTIVATION = 'Solicitud de Activación de Caudal', 'Solicitud de Activación de Caudal'

class FlowRequest(BaseRequestReport):
    """Modelo para solicitudes de caudal."""
    id = models.IntegerField(primary_key=True, verbose_name="ID", help_text="Identificador único de la solicitud/reporte")
    flow_request_type = models.CharField(max_length=80, choices=FlowRequestType.choices, verbose_name="Tipo de solicitud", help_text="Tipo de solicitud de caudal")
    requested_flow = models.FloatField(null=True, blank=True, verbose_name="Caudal solicitado (L/s)", help_text="Valor del caudal solicitado en litros por segundo")
    is_approved = models.BooleanField(default=False, verbose_name="Fue aprobada", help_text="Indica si la solicitud fue aprobada o no")
    requires_delegation = models.BooleanField(default=False, verbose_name="Requiere delegación", help_text="Indica si la solicitud requiere delegación")

    class Meta(BaseRequestReport.Meta):
        verbose_name = "Solicitud de caudal"
        verbose_name_plural = "Solicitudes de caudal"

    def __str__(self):
        return f"{self.flow_request_type} de {self.created_by.get_full_name()} para {self.lot} - {self.status}"

    # --- Propiedades Cacheadas ---
    @cached_property
    def _get_device(self):
        if not self.lot:
            return None
        return IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()

    def _validate_requested_flow(self): # PENDIENTE
        ''' Asegura que el caudal solicitado sea válido '''
        if self.flow_request_type in {FlowRequestType.FLOW_CHANGE, FlowRequestType.FLOW_ACTIVATION}:
            if self.requested_flow is None:
                raise ValueError("El caudal es obligatorio para la solicitud.")
            # Validar rango de caudal solicitado
            if self.requested_flow < 1 or self.requested_flow >= 11.7:
                raise ValueError("El caudal solicitado debe estar dentro del rango de 1 L/seg a 11.7 L/seg.")

    def _check_caudal_flow_inactive(self): # PENDIENTE
        ''' Verifica que el lote tenga un caudal activo '''
        device = self._get_device
        if device.actual_flow in (0, None):
            if self.flow_request_type == FlowRequestType.FLOW_CHANGE:
                raise ValueError("El caudal del lote está inactivo. Debes solicitar activarlo primero.")
            elif self.flow_request_type == FlowRequestType.FLOW_TEMPORARY_CANCEL:
                raise ValueError("El caudal del lote está inactivo. No es necesario solicitar cancelación temporal.")

    def _validate_pending_change_request(self): # PENDIENTE
        ''' Valida que no existan solicitudes de cambio de caudal pendientes para el lote. '''
        if self.flow_request_type == FlowRequestType.FLOW_CHANGE:
            if FlowRequest.objects.filter(lot=self.lot).exclude(status='Finalizado').exclude(pk=self.pk).exists():
                raise ValueError("El lote elegido ya cuenta con una solicitud de cambio de caudal en curso.")

    def _validate_pending_cancel_request(self): # PENDIENTE
        ''' Valida que no existan solicitudes pendientes de cancelación temporal para el mismo lote. '''
        if self.flow_request_type == FlowRequestType.FLOW_CHANGE:
            if FlowRequest.objects.filter(lot=self.lot, flow_request_type__in=[FlowRequestType.FLOW_TEMPORARY_CANCEL, FlowRequestType.FLOW_DEFINITIVE_CANCEL]).exclude(status='Finalizado').exists():
                raise ValueError("El lote elegido cuenta con una solicitud de cancelación de caudal en curso.")

    def _validate_requested_flow_uniqueness(self): # PENDIENTE
        ''' Valida que el caudal solicitado no sea igual al actual '''
        if self.flow_request_type == FlowRequestType.FLOW_CHANGE:
            device = self._get_device
            if self.requested_flow is not None and device.actual_flow == self.requested_flow:
                raise ValueError("El caudal solicitado es el mismo que se encuentra disponible. Intente con un valor diferente.")

    def _validate_pending_temporary_request(self): # PENDIENTE
        ''' Valida que no existan solicitudes pendientes de cancelación temporal para el mismo lote. '''
        if self.flow_request_type == FlowRequestType.FLOW_TEMPORARY_CANCEL:
            if FlowRequest.objects.filter(lot=self.lot, flow_request_type=FlowRequestType.FLOW_TEMPORARY_CANCEL).exclude(status='Finalizado').exclude(pk=self.pk).exists():
                raise ValueError("El lote elegido cuenta con una solicitud de cancelación temporal de caudal en curso.")

    def _validate_pending_definitive_request(self): # PENDIENTE
        ''' Valida que no existan solicitudes pendientes de cancelación definitiva para el mismo lote. '''
        if self.flow_request_type in {FlowRequestType.FLOW_TEMPORARY_CANCEL, FlowRequestType.FLOW_DEFINITIVE_CANCEL}:
            if self.status != 'Finalizado' and FlowRequest.objects.filter(lot=self.lot, flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL).exclude(status='Finalizado').exclude(pk=self.pk).exists():
                raise ValueError("El lote elegido cuenta con una solicitud de cancelación definitiva de caudal en curso.")

    def _validate_pending_activation_request(self):
        ''' Valida que no existan solicitudes pendientes de activación para el mismo lote. '''
        if FlowRequest.objects.filter(lot=self.lot, status='Pendiente').exclude(pk=self.pk).exists():
            raise ValueError("El lote elegido cuenta con una solicitud de activación de caudal en curso.")

    def _validate_actual_flow_activated(self):
        ''' Valida que el caudal actual del lote esté activo '''
        device = self._get_device
        if device.actual_flow > 0:
            raise ValueError("El caudal del lote ya está activo. No es necesario solicitar activación.")

    def _apply_requested_flow_to_device(self): # PENDIENTE
        ''' Aplica el caudal solicitado al dispositivo (válvula) asociado '''
        if self.flow_request_type in {FlowRequestType.FLOW_CHANGE, FlowRequestType.FLOW_TEMPORARY_CANCEL, FlowRequestType.FLOW_ACTIVATION}:
            device = self._get_device
            if self.is_approved == True:
                device.actual_flow = self.requested_flow
                device.save()
                self.status == 'Finalizado' # Marcar como 'Finalizado' la solicitud

    def _auto_reject_temporary_cancel_request(self): # PENDIENTE
        ''' Cambia el estado de una solicitud de cancelación temporal (de 'Pendiente' a 'Finalizado') si se crea una solicitud de cancelación definitiva '''
        if self.flow_request_type == FlowRequestType.FLOW_DEFINITIVE_CANCEL:
            flow_cancel_request = FlowRequest.objects.filter(lot=self.lot, flow_request_type=FlowRequestType.FLOW_TEMPORARY_CANCEL).exclude(status='Finalizado').exclude(pk=self.pk).first()
            if flow_cancel_request:
                flow_cancel_request.is_approved = False # Marcar como 'False' la aprobación de la solicitud temporal
                flow_cancel_request.status = 'Finalizado' # Marcar como 'Finalizado' la solicitud temporal
                flow_cancel_request.observations = 'Finalizado de forma automática: El usuario ha solicitado una cancelación definitiva.'
                flow_cancel_request.save()

    def _apply_cancel_flow_to_device(self): # PENDIENTE
        ''' Aplica la cancelación de caudal al dispositivo (válvula) asociado, y al lote (si es definitiva) '''
        device = self._get_device
        # Si es cancelación temporal
        if self.flow_request_type == FlowRequestType.FLOW_TEMPORARY_CANCEL:
            if self.is_approved == True:
                device.actual_flow = 0 # Desactivar el caudal del lote
                device.save()
                self.status = 'Finalizado'
        # Si es cancelación definitiva
        if self.flow_request_type == FlowRequestType.FLOW_DEFINITIVE_CANCEL:
            device.actual_flow = 0 # Desactivar el caudal del lote
            device.id_lot.is_activate = False # Desactivar el lote
            device.id_lot.save()
            self.status = 'Finalizado'

    def clean(self):
        super().clean()
        self._validate_requested_flow()
        self._check_caudal_flow_inactive()
        self._validate_pending_change_request()
        self._validate_pending_cancel_request()
        self._validate_requested_flow_uniqueness()
        self._validate_pending_temporary_request()
        self._validate_pending_definitive_request()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._apply_requested_flow_to_device()
        self._auto_reject_temporary_cancel_request()
        self._apply_cancel_flow_to_device()

#----------------------------------------------------------------------------
"""
class FlowChangeRequest(BaseRequestReport):
    """#Modelo para almacenar las solicitudes de cambio de caudal.
"""
    requested_flow = models.FloatField(verbose_name="Caudal solicitado (L/s)", help_text="Valor del caudal solicitado en litros por segundo")

    class Meta(BaseRequestReport.Meta):
        verbose_name = "Solicitud de cambio de caudal"
        verbose_name_plural = "Solicitudes de cambio de caudal"

    def __str__(self):
        return f"Solicitud de {self.user.get_full_name()} para {self.lot} ({self.requested_flow} L/s) - {self.status}"

    def _check_caudal_flow_inactive(self): # HECHO
        ''' Verifica que el lote tenga un caudal activo '''
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if device.actual_flow in (0, None):
            raise ValueError("El caudal del lote está inactivo. Debes solicitar activarlo primero.")

    def _validate_pending_change_request(self): # HECHO
        ''' Valida que no existan solicitudes de cambio de caudal pendientes para el lote. '''
        if FlowChangeRequest.objects.filter(lot=self.lot, status='Pendiente').exclude(pk=self.pk).exists():
            raise ValueError("El lote elegido ya cuenta con una solicitud de cambio de caudal en curso.")

    def _validate_pending_cancel_request(self): # HECHO
        ''' Valida que no existan solicitudes pendientes de cancelación temporal para el mismo lote. '''
        if FlowCancelRequest.objects.filter(lot=self.lot, status='Pendiente', cancel_type__in=['temporal', 'definitiva']).exists():
            raise ValueError("El lote elegido cuenta con una solicitud de cancelación de caudal en curso.")

    def _validate_requested_flow_uniqueness(self): # HECHO
        ''' Valida que el caudal solicitado no sea igual al actual '''
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if self.requested_flow is not None and device.actual_flow == self.requested_flow:
            raise ValueError("El caudal solicitado es el mismo que se encuentra disponible. Intente con un valor diferente.")

    def clean(self):
        super().clean()
        self._check_caudal_flow_inactive()
        self._validate_pending_change_request()
        self._validate_pending_cancel_request()
        self._validate_requested_flow()
        self._validate_requested_flow_uniqueness()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._apply_requested_flow_to_device()


class FlowCancelRequest(BaseRequestReport):
    """#Modelo para almacenar las solicitudes de cancelación de caudal.
"""

    CANCEL_TYPE_CHOICES = [
        ('temporal', 'Temporal'),
        ('definitiva', 'Definitiva'),
    ]
    cancel_type = models.CharField(max_length=10, choices=CANCEL_TYPE_CHOICES, verbose_name="Tipo de cancelación", help_text="Indica si la cancelación es temporal o definitiva")
    observations = models.CharField(max_length=200, verbose_name="Observaciones", help_text="Motivo o detalles de la solicitud de cancelación (5 a 200 caracteres)")

    class Meta(BaseRequestReport.Meta):
        verbose_name = "Solicitud de cancelación de caudal"
        verbose_name_plural = "Solicitudes de cancelación de caudal"

    def __str__(self):
        return f"{self.user} solicita cancelación {self.cancel_type} de caudal para {self.lot} ({self.status})"

    def _validate_pending_temporary_request(self): # HECHO
        ''' Valida que no existan solicitudes pendientes de cancelación temporal para el mismo lote. '''
        if self.cancel_type != 'definitiva' and FlowCancelRequest.objects.filter(lot=self.lot, status='Pendiente', cancel_type='temporal').exclude(pk=self.pk).exists():
            raise ValueError("El lote elegido cuenta con una solicitud de cancelación temporal de caudal en curso.")

    def _validate_pending_definitive_request(self):
        ''' Valida que no existan solicitudes pendientes de cancelación definitiva para el mismo lote. '''
        if self.status != 'rechazada' and FlowCancelRequest.objects.filter(lot=self.lot, status='Pendiente', cancel_type='definitiva').exclude(pk=self.pk).exists():
            raise ValueError("El lote elegido cuenta con una solicitud de cancelación definitiva de caudal en curso.")

    def _check_caudal_flow_inactive(self):
        ''' Verifica que el lote tenga un caudal activo '''
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if self.cancel_type == 'temporal' and device.actual_flow in (0, None):
            raise ValueError("El caudal del lote está inactivo. No es necesario solicitar cancelación temporal.")

    def _auto_reject_temporary_cancel_request(self):
        ''' Cambia el estado de una solicitud de cancelación temporal (de 'Pendiente' a 'rechazada') si se crea una solicitud de cancelación definitiva '''
        flow_cancel_request = FlowCancelRequest.objects.filter(lot=self.lot, status='Pendiente', cancel_type='temporal').exclude(pk=self.pk).first()
        if self.cancel_type == 'definitiva' and flow_cancel_request:
            flow_cancel_request.status = 'rechazada' # Rechazar la solicitud temporal
            flow_cancel_request.observations = 'Rechazada de forma automática: El usuario ha solicitado una cancelación definitiva.'
            flow_cancel_request.save()

    def _apply_cancel_flow_to_device(self):
        ''' Aplica la cancelación de caudal al dispositivo (válvula) asociado, y al lote (si es definitiva) '''
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if self.status == 'aprobada':
            device.actual_flow = 0 # Desactivar el caudal del lote
            device.save()
            if self.cancel_type == 'definitiva':
                device.id_lot.is_activate = False # Desactivar el lote
                device.id_lot.save()

    def clean(self):
        super().clean()
        self._validate_pending_definitive_request()
        self._validate_pending_temporary_request()
        self._check_caudal_flow_inactive()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._auto_reject_temporary_cancel_request()
        self._apply_cancel_flow_to_device()


class FlowActivationRequest(BaseRequestReport):
    """#Modelo para solicitudes de activación de caudal.
"""
    requested_flow = models.FloatField(verbose_name="Caudal solicitado (L/s)", help_text="Valor del caudal solicitado en litros por segundo")
    observations = models.CharField(max_length=300, blank=True, null=True, verbose_name="Observaciones", help_text="Observaciones del usuario (opcional, hasta 300 caracteres)")

    class Meta(BaseRequestReport.Meta):
        verbose_name = "Solicitud de activación de caudal"
        verbose_name_plural = "Solicitudes de activación de caudal"

    def __str__(self):
        return f"{self.user} solicita activación de caudal para {self.lot} ({self.status})"

    def _validate_pending_activation_request(self):
        ''' Valida que no existan solicitudes pendientes para el mismo lote. '''
        if FlowActivationRequest.objects.filter(lot=self.lot, status='Pendiente').exclude(pk=self.pk).exists():
            raise ValueError("El lote elegido cuenta con una solicitud de activación de caudal en curso.")

    def _validate_actual_flow_activated(self):
        ''' Valida que el caudal actual del lote esté activo '''
        device = IoTDevice.objects.filter(id_lot=self.lot, device_type__device_id=VALVE_4_ID).first()
        if device.actual_flow > 0:
            raise ValueError("El caudal del lote ya está activo. No es necesario solicitar activación.")

    def clean(self):
        super().clean()
        self._validate_pending_activation_request()
        self._validate_requested_flow()
        self._validate_actual_flow_activated()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._apply_requested_flow_to_device()
"""