
from rest_framework import serializers
from .models import ClimateRecord

class ClimateRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClimateRecord
        fields = '__all__'
        read_only_fields = ['luminiscencia', 'final_date']  # Estos campos se calculan automáticamente