from django.utils import timezone
from rest_framework import serializers
from .models import FlowChangeRequest
from iot.models import IoTDevice, VALVE_4_ID

class FlowChangeRequestSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitudes de cambio de caudal."""

    class Meta:
        model = FlowChangeRequest
        fields = '__all__'
        read_only_fields = ['user', 'device', 'plot', 'status', 'created_at', 'reviewed_at']

    def validate(self, attrs):
        lot = attrs.get('lot')
        requested_flow = attrs.get('requested_flow')
        user = self.context['request'].user

        # Validar dueño del predio
        if lot and lot.plot.owner != user:
            raise serializers.ValidationError("Solo el dueño del predio puede solicitar el cambio de caudal para este lote.")

        # Buscar el dispositivo IoT de tipo válvula 4" asociado al lote
        device = IoTDevice.objects.filter(id_lot=lot, device_type__device_id=VALVE_4_ID).first()
        if not device:
            raise serializers.ValidationError("El lote no tiene una válvula 4\" asociada.")

        # Validar caudal igual al actual
        if requested_flow is not None and device.actual_flow == requested_flow:
            raise serializers.ValidationError(
                {"requested_flow": "Ya tienes un caudal activo con ese valor. Debes solicitar un valor diferente."}
            )

        attrs['plot'] = lot.plot
        attrs['device'] = device
        return attrs

    def create(self, validated_data):
        # Asignar usuario automáticamente
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class FlowChangeRequestStatusSerializer(serializers.ModelSerializer):
    """Serializer para actualizar el estado de la solicitud de cambio de caudal."""

    class Meta:
        model = FlowChangeRequest
        fields = ['status', 'reviewed_at']
        read_only_fields = ['reviewed_at']

    def validate_status(self, value):
        if value not in ['aprobada', 'rechazada']:
            raise serializers.ValidationError("Solo se permite aprobar o rechazar la solicitud.")
        return value

    def update(self, instance, validated_data):
        if instance.status in ['aprobada', 'rechazada']:
            raise serializers.ValidationError(
                {"status": "No se puede cambiar el estado una vez revisada la solicitud."}
            )
        validated_data['reviewed_at'] = timezone.now()
        return super().update(instance, validated_data)