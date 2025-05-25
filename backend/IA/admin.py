from django.contrib import admin
from .models import ClimateRecord, ConsuptionPredictionLot,ConsuptionPredictionBocatoma
import csv
from django.http import HttpResponse

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

@admin.register(ConsuptionPredictionLot)
class ConsuptionPredictionLotAdmin(admin.ModelAdmin):
    # Campos que se muestran en la lista de objetos en el panel de administración
    list_display = (
        'code_prediction',
        'lot',
        'user',
        'period_time',
        'consumption_prediction',
        'date_prediction',
        'created_at',
        'final_date',
    )

    # Campos por los que se puede buscar en el panel de administración
    search_fields = (
        'code_prediction',
        'lot__name', # Permite buscar por el nombre del lote (asumiendo que Lot tiene un campo 'name')
        'user__username', # Permite buscar por el nombre de usuario
        'user__email', # Permite buscar por el email del usuario
    )

    # Campos por los que se puede filtrar la lista de objetos
    list_filter = (
        'period_time',
        'created_at',
        'final_date',
        'lot', # Puedes filtrar por lotes específicos
        'user', # Puedes filtrar por usuarios específicos
    )

    # Campos de solo lectura en el formulario de edición/creación
    readonly_fields = (
        'created_at',
        'final_date',
        'consumption_prediction',
        'date_prediction',
        'code_prediction',
    )

    # Si tienes muchos lotes o usuarios, usar raw_id_fields mejora la performance
    # ya que te permite buscar el ID directamente en lugar de cargar todos los objetos.
    # Necesitas importar Lot y CustomUser para que esto funcione.
    # raw_id_fields = ('lot', 'user',)

    # Orden predeterminado de los objetos en la lista
    ordering = ('-created_at',) # Ordena por fecha de creación descendente

    # Campos que se muestran en el formulario de edición/creación
    # Puedes organizarlos en fieldsets para mayor claridad
    fieldsets = (
        (None, {
            'fields': ('lot', 'user', 'period_time',)
        }),
        ('Detalles de la Predicción', {
            'fields': ('consumption_prediction', 'code_prediction', 'created_at', 'final_date',)
        }),
    )

    # Opcional: Añadir un list_per_page
    list_per_page = 25 # Número de elementos por página en la lista
    
@admin.register(ConsuptionPredictionBocatoma)
class ConsuptionPredictionBocatomaAdmin(admin.ModelAdmin):
    list_display = (
        'code_prediction', 
        'user', 
        'period_time', 
        'date_prediction', 
        'consumption_prediction', 
        'created_at', 
        'final_date'
    )
    list_filter = (
        'period_time', 
        'created_at', 
        'date_prediction', 
        'final_date'
    )
    search_fields = (
        'code_prediction', 
        'user__username'
    )
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.csv'
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = [getattr(obj, field) for field in field_names]
            writer.writerow(row)

        return response
    export_as_csv.short_description = "Exportar seleccionados como CSV"