from rest_framework import viewsets, permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from communication.requests.models import FlowRequest, FlowRequestType
from communication.requests.serializers import FlowRequestSerializer


# Gestiona solicitudes generales de caudal (cambio)
class FlowRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FlowRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return FlowRequest.objects.all()
        return FlowRequest.objects.filter(created_by=user)

    def perform_create(self, serializer):
        # Guarda la solicitud con el usuario actual como creador
        serializer.save(created_by=self.request.user, type='Solicitud')


# Gestiona solicitudes de cancelación (temporal o definitiva)
class CancelFlowRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FlowRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_qs = FlowRequest.objects.filter(
            flow_request_type__in=[
                FlowRequestType.FLOW_TEMPORARY_CANCEL,
                FlowRequestType.FLOW_DEFINITIVE_CANCEL
            ]
        )
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return base_qs
        return base_qs.filter(created_by=user)

    def perform_create(self, serializer):
        # Asocia el usuario creador y marca como tipo 'Solicitud'
        serializer.save(created_by=self.request.user, type='Solicitud')


# Gestiona solicitudes de activación de caudal
class ActivateFlowRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FlowRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_qs = FlowRequest.objects.filter(flow_request_type=FlowRequestType.FLOW_ACTIVATION)
        user = self.request.user
        if user.groups.filter(name="Manager").exists():
            return base_qs
        return base_qs.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, type='Solicitud')


# Permite visualizar el detalle de una solicitud específica
class FlowRequestDetailView(RetrieveAPIView):
    queryset = FlowRequest.objects.all()
    serializer_class = FlowRequestSerializer
    permission_classes = [IsAuthenticated]


# Permite aprobar una solicitud de caudal
class FlowRequestApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            flow = FlowRequest.objects.get(pk=pk)
        except FlowRequest.DoesNotExist:
            return Response({"detail": "Solicitud no encontrada."}, status=404)

        flow.is_approved = True
        flow.status = "Finalizado"
        flow.save()
        return Response({"detail": "Solicitud aprobada."}, status=200)


# Permite rechazar una solicitud de caudal con observaciones
class FlowRequestRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        obs = request.data.get("observations")
        if not obs:
            return Response({"detail": "Debe incluir observaciones del rechazo."}, status=400)

        try:
            flow = FlowRequest.objects.get(pk=pk)
        except FlowRequest.DoesNotExist:
            return Response({"detail": "Solicitud no encontrada."}, status=404)

        flow.is_approved = False
        flow.status = "Finalizado"
        flow.observations = obs
        flow.save()
        return Response({"detail": "Solicitud rechazada."}, status=200)
