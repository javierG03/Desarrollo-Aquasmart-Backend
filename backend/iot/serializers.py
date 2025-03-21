from rest_framework import serializers
from .models import IoTDevice, DeviceType
from plots_lots.models import Plot, Lot  

class IoTDeviceSerializer(serializers.ModelSerializer):
    iot_id = serializers.CharField(read_only=True)  # ID generado automáticamente
    device_type = serializers.PrimaryKeyRelatedField(queryset=DeviceType.objects.all())  
    id_plot = serializers.PrimaryKeyRelatedField(queryset=Plot.objects.all(), allow_null=True, required=False)  # ✅ Permite NULL y no es obligatorio
    id_lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all(), allow_null=True, required=False)  # ✅ Permite NULL y no es obligatorio
    owner_name = serializers.SerializerMethodField(read_only=True)  
    device_type_name = serializers.CharField(source='device_type.name', read_only=True)
    class Meta:
        model = IoTDevice
        fields = ['iot_id', 'id_plot', 'id_lot', 'name', 'device_type', 'is_active', 'characteristics', 'owner_name','device_type_name']

    def get_owner_name(self, obj):
        """ Método para obtener el nombre del dueño del predio """
        return obj.id_plot.owner.get_full_name() if obj.id_plot and obj.id_plot.owner else "Sin dueño"

    def validate(self, data):
        """ Validación personalizada """
        id_plot = data.get('id_plot', None)  # ✅ Puede ser None
        id_lot = data.get('id_lot', None)  
        device_type = data.get('device_type')

        # 1️⃣ Si `id_plot` no es None, validar que existe
        if id_plot:
            plot = Plot.objects.filter(id=id_plot.id).first()
            if not plot:
                raise serializers.ValidationError({"id_plot": "El predio con el ID proporcionado no existe."})

        # 2️⃣ Si `id_lot` no es None, validar que existe y pertenece al `id_plot`
        if id_lot:
            lot = Lot.objects.filter(id=id_lot.id).first()
            if not lot:
                raise serializers.ValidationError({"id_lot": "El lote con el ID proporcionado no existe."})

            if id_plot and lot.plot_id != id_plot.id:
                raise serializers.ValidationError({"id_lot": "El lote no pertenece al predio especificado."})

        # 3️⃣ Validar que no haya más de un dispositivo del mismo tipo por lote
        if id_lot and IoTDevice.objects.filter(id_lot=id_lot, device_type=device_type).exists():
            raise serializers.ValidationError({"device_type": f"Ya existe un dispositivo {device_type} en este lote."})

        return data

class IoTDeviceStatusSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = IoTDevice
        fields = ['is_active']
        read_only_fields = ['iot_id']  # iot_id no se puede modificar

class DeviceTypeSerializer(serializers.ModelSerializer):
    id_plot = serializers.PrimaryKeyRelatedField(
        queryset=Plot.objects.all(),
        allow_null=True,  # Permite valores NULL
        required=False  # No es obligatorio en la API
    )

    class Meta:
        model = DeviceType
        fields = '__all__'  # Incluir todos los campos

    def create(self, validated_data):
        """Genera automáticamente el `device_id`"""
        instance = DeviceType(**validated_data)
        instance.save()
        return instance        