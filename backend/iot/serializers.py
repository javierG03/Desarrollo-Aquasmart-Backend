from rest_framework import serializers
from .models import IoTDevice, DeviceType
from plots_lots.models import Plot, Lot  

class IoTDeviceSerializer(serializers.ModelSerializer):
    iot_id = serializers.CharField(read_only=True)  # ID generado automáticamente
    device_type = serializers.PrimaryKeyRelatedField(queryset=DeviceType.objects.all())  # Referencia a DeviceType

    class Meta:
        model = IoTDevice
        fields = ['iot_id', 'id_plot', 'id_lot', 'name', 'device_type', 'is_active', 'characteristics']

    def validate(self, data):
        """ Validación personalizada """
        # Validar que el predio (id_plot) y lote (id_lot) existan
        if data.get('id_plot') and not Plot.objects.filter(id_plot=data['id_plot']).exists():
            raise serializers.ValidationError("El predio con el ID proporcionado no existe.")

        if data.get('id_lot') and not Lot.objects.filter(id_lot=data['id_lot']).exists():
            raise serializers.ValidationError("El lote con el ID proporcionado no existe.")

        # Validar que no haya más de un dispositivo del mismo tipo por lote
        if data.get('id_lot'):
            if IoTDevice.objects.filter(id_lot=data['id_lot'], device_type=data['device_type']).exists():
                raise serializers.ValidationError(f"Ya existe un dispositivo {data['device_type']} en este lote.")

        return data

class IoTDeviceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = IoTDevice
        fields = ['is_active']
        read_only_fields = ['iot_id']  # iot_id no se puede modificar

class DeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceType
        fields = '__all__'  # Incluir todos los campos

    def create(self, validated_data):
        """Genera automáticamente el `device_id`"""
        instance = DeviceType(**validated_data)
        instance.save()
        return instance        