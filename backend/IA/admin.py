from django.contrib import admin
from .models import ClimateRecord

@admin.register(ClimateRecord)
class ClimateRecordAdmin(admin.ModelAdmin):
    list_display = (
        'datetime', 'tempmax', 'tempmin', 'precip', 'windgust',
        'cloudcover', 'solarradiation', 'sunrise', 'sunset',
        'luminiscencia', 'final_date'
    )
    list_filter = ('datetime', 'final_date', 'cloudcover')
    search_fields = ('datetime',)
    ordering = ('-datetime',)
    date_hierarchy = 'datetime'
    readonly_fields = ('luminiscencia', 'final_date')
    
  