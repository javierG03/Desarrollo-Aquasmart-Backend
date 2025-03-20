from django.db import models
import random

class DeviceType(models.Model):
    device_id = models.CharField(max_length=2, primary_key=True, editable=False)
    name = models.CharField(max_length=50, blank=False, null=False)

    def save(self, *args, **kwargs):
        if not self.device_id:
            last_device = DeviceType.objects.order_by('-device_id').first()
            if last_device:
                new_id = int(last_device.device_id) + 1  # Incrementa el último ID
                self.device_id = f"{new_id:02d}"  # Formatea con dos dígitos
            else:
                self.device_id = "01"  # Primer ID

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class IoTDevice(models.Model):
    iot_id = models.CharField(max_length=7, primary_key=True, editable=False)  # Formato XX-YYYY
    id_plot = models.CharField(max_length=10, blank=True, null=True, verbose_name="ID del Predio")
    id_lot = models.CharField(max_length=15, blank=True, null=True, verbose_name="ID del Lote")
    name = models.CharField(max_length=100, verbose_name="Nombre del Dispositivo")
    device_type = models.ForeignKey(DeviceType, on_delete=models.CASCADE, verbose_name="Tipo de Dispositivo")
    is_active = models.BooleanField(default=True, help_text="Indica si el dispositivo está habilitado", db_index=True, verbose_name="Estado del Dispositivo")
    characteristics = models.CharField(max_length=300, blank=True, null=False, default="Sin características", verbose_name="Características del Dispositivo")

    def save(self, *args, **kwargs):
        if not self.iot_id:
            random_suffix = f"{random.randint(0, 9999):04d}"  # Números aleatorios de 4 dígitos
            self.iot_id = f"{self.device_type.device_id}-{random_suffix}"  # XX-YYYY

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Dispositivo IoT"
        verbose_name_plural = "Dispositivos IoT"

    def __str__(self):
        return f"{self.name} ({self.device_type.name})"
    