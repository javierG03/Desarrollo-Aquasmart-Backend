from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from communication.requests.models import FlowRequest, FlowRequestType
from communication.reports.models import FailureReport
from .models import Assignment
from .serializers import AssignmentSerializer


class PendingItemsListView(APIView):
    """
    Devuelve una lista unificada de solicitudes y reportes pendientes
    para que un administrador pueda gestionarlos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

    
    # Si es manager, ve todo
        if user.groups.filter(name="Manager").exists():
         flow_requests = FlowRequest.objects.exclude(status="Finalizado")
         failure_reports = FailureReport.objects.exclude(status="Finalizado")
        else:
         flow_requests = FlowRequest.objects.filter(created_by=user).exclude(status="Finalizado")
         failure_reports = FailureReport.objects.filter(created_by=user).exclude(status="Finalizado")

    
        # Solicitudes no finalizadas
        flow_requests = FlowRequest.objects.exclude(status="Finalizado")
        # Reportes no finalizados
        failure_reports = FailureReport.objects.exclude(status="Finalizado")

        # Serialización manual simplificada
        data = []

        for fr in flow_requests:
            data.append({
                "id": fr.id,
                "type": "FlowRequest",
                "subtype": fr.flow_request_type,
                "status": fr.status,
                "created_by": fr.created_by.get_full_name(),
                "created_at": fr.created_at,
                "action": "Gestión"
            })

        for rep in failure_reports:
            data.append({
                "id": rep.id,
                "type": "FailureReport",
                "subtype": rep.failure_type,
                "status": rep.status,
                "created_by": rep.created_by.get_full_name(),
                "created_at": rep.created_at,
                "action": "Gestión"
            })

        return Response(sorted(data, key=lambda x: x['created_at'], reverse=True))

class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Crea y lista asignaciones de técnicos para solicitudes/reportes que lo requieren.
    """
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return Assignment.objects.all()
        return Assignment.objects.filter(assigned_by=user)
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)