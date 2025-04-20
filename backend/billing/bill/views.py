
from rest_framework import generics
from .models import Bill
from .serializers import BillSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser


class UserBillListView(generics.ListAPIView):
    """Vista para obtener las facturas de un usuario específico."""
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra las facturas solo para el usuario logueado."""
        user = self.request.user
        queryset = Bill.objects.filter(client=user)  # Filtra por el usuario logueado
        return queryset

class AdminBillListView(generics.ListAPIView):
    """Vista para obtener todas las facturas, accesible solo para administradores."""
    serializer_class = BillSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """Devuelve todas las facturas."""
        return Bill.objects.all()