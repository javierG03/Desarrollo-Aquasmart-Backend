from django.db import models
from datetime import datetime,timedelta


class ClimateRecord(models.Model):
    
    datetime = models.DateTimeField()
    tempmax = models.FloatField()
    tempmin = models.FloatField()
    precip = models.FloatField()
    precipprob = models.FloatField()
    precipcover = models.FloatField() 
    windgust  = models.FloatField()
    windspeed = models.FloatField()
    pressure = models.FloatField()
    cloudcover = models.FloatField()
    solarradiation = models.FloatField()
    sunrise = models.TimeField()
    sunset = models.TimeField()
    luminiscencia = models.FloatField()
    final_date = models.DateTimeField()
    def __str__(self):
        return f"Registro de clima desde {self.datetime} hasta {self.final_date}"
    def save(self, *args,**kwargs):
        if self.luminiscencia is None:
            # calculo de luminiscencia
            base_date= self.datetime.date()
            sunrise = datetime.combine(base_date, self.sunrise)
            sunset = datetime.combine(base_date, self.sunset)
            diference= sunset - sunrise
            luminiscencia_hours = round(diference.total_seconds() / 3600, 2)
            self.luminiscencia = luminiscencia_hours
        # Calcular final_date la fecha final automaticamente 
        if self.final_date is None:
            self.final_date = self.datetime + timedelta(days=7)
       
        super().save(*args, **kwargs)