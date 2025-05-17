from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from datetime import datetime
from django.utils import timezone
from .models import ClimateRecord
from .serializers import ClimateRecordSerializer
from .utils import api_climate_request
import time
from rest_framework.permissions import IsAuthenticated

class ClimateRecordViewSet(viewsets.ModelViewSet):
    queryset = ClimateRecord.objects.all()
    serializer_class = ClimateRecordSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def fetch_climate_data(self, request):
        location = request.data.get('location', "4.60971%2C-74.08175")
        date = request.data.get('date', timezone.now().strftime("%Y-%m-%d"))
        today = timezone.now()

        # Obtener el último registro
        latest_record = ClimateRecord.objects.order_by('-datetime').first()

        if latest_record:
            if latest_record.final_date >= today:
                # Ya hay un registro válido, devolverlo sin hacer petición externa
                serializer = ClimateRecordSerializer(latest_record)
                return Response({
                    "message": "Ya existe un registro con datos válidos.",
                    "record": serializer.data
                }, status=status.HTTP_200_OK)

        # Continuar con la solicitud externa si no hay registro válido
        climate_data = api_climate_request(location, date)

        if not climate_data:
            return Response(
                {"error": "No se pudieron obtener datos de la API de clima"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        days = climate_data.get("days", [])
        if not days:
            return Response(
                {"error": "No se encontraron datos para la fecha especificada"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        saved_records = []
        for day_data in days:
            try:
                datetime_str = day_data.get('datetime')
                datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d")

                sunrise_time = datetime.strptime(day_data.get('sunrise'), "%H:%M:%S").time()
                sunset_time = datetime.strptime(day_data.get('sunset'), "%H:%M:%S").time()

                climate_record = ClimateRecord(
                    datetime=datetime_obj,
                    tempmax=day_data.get('tempmax'),
                    tempmin=day_data.get('tempmin'),
                    precip=day_data.get('precip'),
                    precipprob=day_data.get('precipprob'),
                    precipcover=day_data.get('precipcover'),
                    windgust=day_data.get('windgust'),
                    windspeed=day_data.get('windspeed'),
                    pressure=day_data.get('pressure'),
                    cloudcover=day_data.get('cloudcover'),
                    solarradiation=day_data.get('solarradiation'),
                    sunrise=sunrise_time,
                    sunset=sunset_time,
                    # final_date y luminiscencia deben ser calculados en el modelo
                )

                climate_record.save()
                serializer = ClimateRecordSerializer(climate_record)
                saved_records.append(serializer.data)

            except Exception as e:
                return Response(
                    {"error": f"Error al procesar los datos del clima: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {"message": "Datos climáticos obtenidos y guardados con éxito", "records": saved_records}, 
            status=status.HTTP_201_CREATED
        )

@api_view(['GET'])
def get_latest_climate_data(request):
    """
    Endpoint para obtener el registro climático más reciente.
    """
    try:
        latest_record = ClimateRecord.objects.order_by('-datetime').first()
        print(latest_record)
        if latest_record:
            serializer = ClimateRecordSerializer(latest_record)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "No hay registros climáticos disponibles"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        return Response(
            {"error": f"Error al obtener los datos del clima: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )