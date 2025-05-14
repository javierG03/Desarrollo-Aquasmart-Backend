from rest_framework import serializers
from .models import FlowRequest, FlowRequestType
from iot.models import IoTDevice, VALVE_4_ID

class FlowRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowRequest
        fields = [
            'id',
            'type',
            'created_by',
            'lot',
            'flow_request_type',
            'requested_flow',
            'is_approved',
            'requires_delegation',
            'status',
            'observations',
            'created_at',
            'finalized_at',
        ]
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'finalized_at']

    def validate(self, attrs):
        user = self.context['request'].user
        lot = attrs.get('lot') or getattr(self.instance, 'lot', None)
        flow_request_type = attrs.get('flow_request_type') or getattr(self.instance, 'flow_request_type', None)
        requested_flow = attrs.get('requested_flow') if 'requested_flow' in attrs else getattr(self.instance, 'requested_flow', None)

        # Validar que se envíe el lote
        if not lot:
            raise serializers.ValidationError({"lot": "El lote es obligatorio para la solicitud."})

        # Validar dueño del predio
        if user != lot.plot.owner:
            raise serializers.ValidationError({"owner": "Solo el dueño del predio puede realizar una solicitud para el caudal de este lote."})

        # Validar que el lote esté habilitado
        if lot.is_activate is not True:
            raise serializers.ValidationError("No se puede realizar solicitud de caudal de un lote inhabilitado.")

        # Validar que el lote tenga válvula 4"
        device = IoTDevice.objects.filter(id_lot=lot, device_type__device_id=VALVE_4_ID).first()
        if not device:
            raise serializers.ValidationError("El lote no tiene una válvula 4\" asociada.")

        # Validar caudal solicitado (solo para cambio y activación)
        if flow_request_type in {FlowRequestType.FLOW_CHANGE, FlowRequestType.FLOW_ACTIVATION}:
            if requested_flow is None:
                raise serializers.ValidationError("El caudal es obligatorio para la solicitud.")
            if requested_flow < 1 or requested_flow >= 11.7:
                raise serializers.ValidationError("El caudal solicitado debe estar dentro del rango de 1 L/seg a 11.7 L/seg.")

        # Validar caudal activo para cambio de caudal
        if flow_request_type == FlowRequestType.FLOW_CHANGE and device.actual_flow in (0, None):
            raise serializers.ValidationError("El caudal del lote está inactivo. Debes solicitar activarlo primero.")

        # Validar caudal ya activo en activación
        if flow_request_type == FlowRequestType.FLOW_ACTIVATION and device.actual_flow > 0:
            raise serializers.ValidationError("El caudal del lote ya está activo. No es necesario solicitar activación.")

        # Validar caudal ya inactivo en cancelación temporal
        if flow_request_type == FlowRequestType.FLOW_TEMPORARY_CANCEL and device.actual_flow in (0, None):
            raise serializers.ValidationError("El caudal del lote está inactivo. No es necesario solicitar cancelación temporal.")

        # Validar solicitudes pendientes de cambio de caudal
        if flow_request_type == FlowRequestType.FLOW_CHANGE:
            if FlowRequest.objects.filter(lot=lot, flow_request_type=FlowRequestType.FLOW_CHANGE).exclude(status='Finalizado').exclude(pk=getattr(self.instance, 'pk', None)).exists():
                raise serializers.ValidationError("El lote elegido ya cuenta con una solicitud de cambio de caudal en curso.")

        # Validar solicitudes pendientes de cancelación (temporal o definitiva)
        if flow_request_type == FlowRequestType.FLOW_CHANGE:
            if FlowRequest.objects.filter(
                lot=lot,
                flow_request_type__in=[FlowRequestType.FLOW_TEMPORARY_CANCEL, FlowRequestType.FLOW_DEFINITIVE_CANCEL]
            ).exclude(status='Finalizado').exists():
                raise serializers.ValidationError("El lote elegido cuenta con una solicitud de cancelación de caudal en curso.")

        # Validar caudal solicitado no igual al actual
        if flow_request_type == FlowRequestType.FLOW_CHANGE and requested_flow is not None and device.actual_flow == requested_flow:
            raise serializers.ValidationError("El caudal solicitado es el mismo que se encuentra disponible. Intente con un valor diferente.")

        # Validar solicitudes pendientes de cancelación temporal
        if flow_request_type == FlowRequestType.FLOW_TEMPORARY_CANCEL:
            if FlowRequest.objects.filter(
                lot=lot,
                flow_request_type=FlowRequestType.FLOW_TEMPORARY_CANCEL
            ).exclude(status='Finalizado').exclude(pk=getattr(self.instance, 'pk', None)).exists():
                raise serializers.ValidationError("El lote elegido cuenta con una solicitud de cancelación temporal de caudal en curso.")

        # Validar solicitudes pendientes de cancelación definitiva
        if flow_request_type in {FlowRequestType.FLOW_TEMPORARY_CANCEL, FlowRequestType.FLOW_DEFINITIVE_CANCEL}:
            if FlowRequest.objects.filter(
                lot=lot,
                flow_request_type=FlowRequestType.FLOW_DEFINITIVE_CANCEL
            ).exclude(status='Finalizado').exclude(pk=getattr(self.instance, 'pk', None)).exists():
                raise serializers.ValidationError("El lote elegido cuenta con una solicitud de cancelación definitiva de caudal en curso.")

        # Validar solicitudes pendientes de activación
        if flow_request_type == FlowRequestType.FLOW_ACTIVATION:
            if FlowRequest.objects.filter(
                lot=lot,
                flow_request_type=FlowRequestType.FLOW_ACTIVATION,
                status='Pendiente'
            ).exclude(pk=getattr(self.instance, 'pk', None)).exists():
                raise serializers.ValidationError("El lote elegido cuenta con una solicitud de activación de caudal en curso.")

        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['type'] = 'Solicitud'
        return super().create(validated_data)