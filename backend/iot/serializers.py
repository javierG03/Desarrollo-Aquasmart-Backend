from rest_framework import serializers
from .models import IoTDevice, DeviceType
from plots_lots.models import Plot, Lot  

class IoTDeviceSerializer(serializers.ModelSerializer):
    iot_id = serializers.CharField(read_only=True)  # ID generado automáticamente
    device_type = serializers.PrimaryKeyRelatedField(queryset=DeviceType.objects.all())  # Relación con DeviceType
    id_plot = serializers.PrimaryKeyRelatedField(queryset=Plot.objects.all())  # 🔹 Asegura que id_plot es un objeto, no un string
    owner_name = serializers.SerializerMethodField(read_only=True)  # 🔹 Solo lectura

    class Meta:
        model = IoTDevice
        fields = ['iot_id', 'id_plot', 'id_lot', 'name', 'device_type', 'is_active', 'characteristics', 'owner_name']

    def get_owner_name(self, obj):
        """ Método para obtener el nombre del dueño del predio """
        return obj.id_plot.owner.get_full_name() if obj.id_plot and obj.id_plot.owner else "Sin dueño"

    def validate(self, data):
        """ Validación personalizada """
        id_plot = data.get('id_plot')
        id_lot = data.get('id_lot')
        device_type = data.get('device_type')

        # 1️⃣ Validar que el predio (id_plot) existe
        plot = Plot.objects.filter(id_plot=id_plot).first()
        if not plot:
            raise serializers.ValidationError({"id_plot": "El predio con el ID proporcionado no existe."})

        # 2️⃣ Validar que el lote (id_lot) existe y pertenece al predio (id_plot)
        lot = Lot.objects.filter(id_lot=id_lot, plot=plot).first()
        if not lot:
            raise serializers.ValidationError({"id_lot": "El lote no existe en el predio especificado."})

        # 3️⃣ Validar que no haya más de un dispositivo del mismo tipo por lote
        if IoTDevice.objects.filter(id_lot=id_lot, device_type=device_type).exists():
            raise serializers.ValidationError({"device_type": f"Ya existe un dispositivo {device_type} en este lote."})

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