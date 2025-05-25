from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.generics import (
    RetrieveAPIView, CreateAPIView, ListAPIView
)
from rest_framework.permissions import IsAuthenticated, BasePermission, IsAdminUser
from django.contrib.auth import get_user_model
from communication.requests.models import FlowRequest
from communication.requests.serializers import FlowRequestSerializer
from communication.reports.models import FailureReport
from communication.reports.serializers import FailureReportSerializer

from .models import MaintenanceReport, Assignment
from .serializers import MaintenanceReportSerializer, AssignmentSerializer

from .models import MaintenanceReport, Assignment
from .serializers import MaintenanceReportSerializer, AssignmentSerializer
from communication.permissions import CanAccessAssignmentView
from django.db.models import Q 
User = get_user_model()


class AdminRequestOrReportUnifiedDetailView(APIView):
    """
    Devuelve el detalle de una solicitud o reporte según el ID, sin importar el usuario.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        flow = FlowRequest.objects.filter(pk=pk).first()
        if flow:
            return Response(FlowRequestSerializer(flow).data)

        report = FailureReport.objects.filter(pk=pk).first()
        if report:
            return Response(FailureReportSerializer(report).data)

        return Response({"detail": "No se encontró una solicitud o reporte con ese ID."}, status=404)


class AllRequestsAndReportsView(APIView):
    """
    Devuelve todas las solicitudes y reportes de todos los usuarios (uso administrativo).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        flow_requests = FlowRequest.objects.all()
        failure_reports = FailureReport.objects.all()

        flow_data = FlowRequestSerializer(flow_requests, many=True).data
        report_data = FailureReportSerializer(failure_reports, many=True).data

        return Response({
            "flow_requests": flow_data,
            "failure_reports": report_data
        })
    


class IsAdminOrTechnicianOrOperator(BasePermission):
    """
    Permite acceso si el usuario es admin o pertenece a Técnicos u Operadores.
    """
    def has_permission(self, request, view):
        user = request.user
        return (
            user and user.is_authenticated and (
                user.is_staff or
                user.groups.filter(name__in=["Técnicos", "Operadores"]).exists()
            )
        )

class AssignmentViewSet(viewsets.ModelViewSet):
   
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated, CanAccessAssignmentView]

    def get_queryset(self):
        """
        Filtra las asignaciones según los permisos específicos del usuario.
        """
        user = self.request.user
        
        # Superusuarios ven todo
        if user.is_superuser:
            return self.queryset.all()
            
        # Usuarios con permiso global de vista ven todo
        if user.has_perm('communication.view_all_assignments'):
            return self.queryset.all()
            
        # Usuarios normales solo ven las que crearon o les fueron asignadas
        return self.queryset.filter(
            Q(assigned_by=user) | Q(assigned_to=user)
        )

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class FlowRequestAssignmentDetailView(RetrieveAPIView):
    """
    Devuelve los detalles de una solicitud asignada (para gestión).
    """
    queryset = FlowRequest.objects.all()
    serializer_class = FlowRequestSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]


class FailureReportAssignmentDetailView(RetrieveAPIView):
    """
    Devuelve los detalles de un reporte asignado (para gestión).
    """
    queryset = FailureReport.objects.all()
    serializer_class = FailureReportSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]


class TechnicianAssignedItemsView(ListAPIView):
    """
    Lista todas las solicitudes o reportes asignados al técnico autenticado.
    """
    permission_classes = [IsAuthenticated,IsAdminUser]
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        return Assignment.objects.filter(assigned_to=self.request.user)


class AssignmentDetailView(RetrieveAPIView):
    """
    Detalle completo de una asignación específica (flujo o reporte).
    """
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]


class MaintenanceReportCreateView(CreateAPIView):
    """
    Permite al técnico crear un informe de mantenimiento.
    """
    permission_classes = [IsAuthenticated,IsAdminOrTechnicianOrOperator ]
    serializer_class = MaintenanceReportSerializer

    def perform_create(self, serializer):
        serializer.save()


class MaintenanceReportListView(ListAPIView):
    """
    Lista todos los informes de mantenimiento.
    Técnicos, operadores y admins ven todos. Otros ven solo los suyos.
    Lista todos los informes de mantenimiento. Técnicos ven los propios, managers ven todos.
    """
    serializer_class = MaintenanceReportSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTechnicianOrOperator]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name__in=["Técnicos", "Operadores"]).exists():
            if user.groups.filter(name="Manager").exists():
                return MaintenanceReport.objects.all()
            return MaintenanceReport.objects.filter(assignment__assigned_to=user)


        if user.groups.filter(name="Manager").exists():
            return MaintenanceReport.objects.all()
        return MaintenanceReport.objects.filter(assignment__assigned_to=user)


class MaintenanceReportDetailView(RetrieveAPIView):
    """
    Muestra los detalles de un informe de mantenimiento específico.
    """
    queryset = MaintenanceReport.objects.all()
    serializer_class = MaintenanceReportSerializer
    permission_classes = [IsAuthenticated,IsAdminOrTechnicianOrOperator]


class ApproveMaintenanceReportView(APIView):
    """
    Permite aprobar un informe de mantenimiento.
    Solo accesible por administradores, técnicos u operadores autorizados.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        try:
            report = MaintenanceReport.objects.get(pk=pk)
        except MaintenanceReport.DoesNotExist:
            return Response({"detail": "Informe no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if report.is_approved:
            return Response({"detail": "El informe ya fue aprobado."}, status=status.HTTP_400_BAD_REQUEST)

        report.is_approved = True
        report.save()
        return Response({"detail": "Informe aprobado correctamente."})


class ReassignAssignmentView(APIView):
    """
    Permite reasignar una solicitud o reporte a otro técnico u operador.
    """
    permission_classes = [IsAuthenticated,  IsAdminUser]
    def post(self, request, pk):
        try:
            old_assignment = Assignment.objects.get(pk=pk)
        except Assignment.DoesNotExist:
            return Response({"detail": "Asignación no encontrada."}, status=404)

        data = request.data.copy()
        data['reassigned'] = True

        # Copiamos la solicitud o reporte original
        if old_assignment.flow_request:
            data['flow_request'] = old_assignment.flow_request.pk
        elif old_assignment.failure_report:
            data['failure_report'] = old_assignment.failure_report.pk

        serializer = AssignmentSerializer(
            data=data,
            context={
                'request': request,
                'is_reassignment': True  # Para el serializer
            }
        )

        if serializer.is_valid():
            serializer.save(assigned_by=request.user)
            return Response({"detail": "Reasignación creada correctamente."})
        else:
            return Response({
                "detail": "No se pudo completar la reasignación.",
                "errors": serializer.errors
            }, status=400)
