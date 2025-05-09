from rest_framework import viewsets, permissions
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from communication.reports.models import FailureReport, TypeReport
from communication.reports.serializers import FailureReportSerializer

class WaterSupplyFailureReportViewSet(viewsets.ModelViewSet):
    """
    Gestiona los reportes de fallos en el suministro de agua.
    """
    queryset = FailureReport.objects.filter(failure_type=TypeReport.WATER_SUPPLY_FAILURE)
    serializer_class = FailureReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Devuelve solo los reportes creados por el usuario (o todos si es gerente)
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return self.queryset
        return self.queryset.filter(created_by=user)

    def perform_create(self, serializer):
        # Asocia automáticamente el usuario autenticado
        serializer.save(created_by=self.request.user, type='Reporte', failure_type=TypeReport.WATER_SUPPLY_FAILURE)

class AppFailureReportViewSet(viewsets.ModelViewSet):
    """
    Gestiona los reportes de fallos en el aplicativo.
    """
    queryset = FailureReport.objects.filter(failure_type=TypeReport.APPLICATION_FAILURE)
    serializer_class = FailureReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Retorna reportes creados por el usuario autenticado
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return self.queryset
        return self.queryset.filter(created_by=user)

    def perform_create(self, serializer):
        # Guarda el reporte como tipo 'Aplicativo'
        serializer.save(created_by=self.request.user, type='Reporte', failure_type=TypeReport.APPLICATION_FAILURE, lot=None, plot=None)

class FailureReportDetailView(RetrieveAPIView):
    """
    Vista de detalle de un reporte de fallos.
    """
    queryset = FailureReport.objects.all()
    serializer_class = FailureReportSerializer
    permission_classes = [IsAuthenticated]