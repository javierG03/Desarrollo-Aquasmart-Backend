# Generated by Django 5.1.6 on 2025-04-23 03:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('iot', '0011_alter_devicetype_options'),
        ('plots_lots', '0008_croptype_lot_crop_name_alter_lot_crop_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FlowChangeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requested_flow', models.FloatField(help_text='Valor del caudal solicitado en litros por segundo', verbose_name='Caudal solicitado (L/s)')),
                ('status', models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada')], default='pendiente', help_text='Estado actual de la solicitud', max_length=10, verbose_name='Estado')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora en que se creó la solicitud', verbose_name='Fecha solicitud')),
                ('reviewed_at', models.DateTimeField(blank=True, help_text='Fecha y hora en que la solicitud fue revisada (aprobada o rechazada)', null=True, verbose_name='Fecha revisión')),
                ('device', models.ForeignKey(help_text='Dispositivo IoT (válvula) asociado a la solicitud', on_delete=django.db.models.deletion.CASCADE, to='iot.iotdevice', verbose_name='Dispositivo')),
                ('lot', models.ForeignKey(blank=True, help_text='Lote al que se le solicita el cambio de caudal', null=True, on_delete=django.db.models.deletion.CASCADE, to='plots_lots.lot', verbose_name='Lote')),
                ('plot', models.ForeignKey(blank=True, help_text='Predio de la válvula principal (si es válvula principal de predio)', null=True, on_delete=django.db.models.deletion.CASCADE, to='plots_lots.plot', verbose_name='Predio')),
                ('user', models.ForeignKey(help_text='Usuario que realiza la solicitud de cambio de caudal', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Solicitante')),
            ],
            options={
                'verbose_name': 'Solicitud de cambio de caudal',
                'verbose_name_plural': 'Solicitudes de cambio de caudal',
            },
        ),
    ]
