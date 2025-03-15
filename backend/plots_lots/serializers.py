from rest_framework import serializers
from .models import Plot
from users.models import CustomUser
from rest_framework.exceptions import NotFound
class PlotSerializer(serializers.ModelSerializer):
    owner = serializers.CharField()
    class Meta:
        model = Plot
        fields = ['id_plot','owner','plot_name', 'latitud','longitud','plot_extension', 'registration_date']
        read_only_fields = ['id_plot', 'registration_date']  # Estos campos no se pueden modificar
        


    def validate_owner(self, value):
        """Validar que el usuario existe en la base de datos."""
        try:
            user = CustomUser.objects.get(document=value)
        except CustomUser.DoesNotExist:
            raise NotFound("El usuario no está registrado.")

        return user  # Retornar el objeto en lugar del ID

    def validate(self, data):
        """Validación para evitar duplicados en la georeferenciación."""
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        if Plot.objects.filter(latitud=latitud, longitud=longitud).exists():
            raise serializers.ValidationError("La georeferenciación ya está asignada a otro predio.")
        return data