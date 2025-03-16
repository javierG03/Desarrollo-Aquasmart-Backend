from rest_framework import serializers
from .models import Plot
from users.models import CustomUser
from rest_framework.exceptions import NotFound
class PlotSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        error_messages={'does_not_exist': "El usuario asignado no está registrado"}
    )

    class Meta:
        model = Plot
        fields = ['id_plot', 'owner', 'plot_name', 'latitud', 'longitud', 'plot_extension', 'registration_date','is_activate']
        read_only_fields = ['id_plot', 'registration_date','is_activate']

    
    def validate(self, data):
        """Validación personalizada para evitar duplicados en la georeferenciación."""
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        if Plot.objects.filter(latitud=latitud, longitud=longitud).exists():
            raise serializers.ValidationError("La georeferenciación ya está asignada a otro predio.")
        return data