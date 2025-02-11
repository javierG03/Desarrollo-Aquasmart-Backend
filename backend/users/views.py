from rest_framework import generics  
from .models import CustomUser  
from .serializers import CustomUserSerializer  
from rest_framework.permissions import IsAdminUser, IsAuthenticated  

class CustomUserCreateView(generics.CreateAPIView):
    """
    Vista para la creación de usuarios personalizados.
    
    - Usa `CreateAPIView` para manejar la creación de usuarios.
    - `queryset` define el conjunto de datos sobre el que opera la vista.
    - `serializer_class` especifica el serializador utilizado para validar y transformar los datos.
    - `permission_classes` actualmente está vacío, lo que significa que cualquiera puede acceder a esta vista.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = []  # Sin restricciones de acceso (puede ser cambiado según necesidad)

class CustomUserListView(generics.ListAPIView):
    """
    Vista para listar los usuarios personalizados.
    
    - Usa `ListAPIView` para manejar la recuperación de la lista de usuarios.
    - `queryset` obtiene todos los usuarios registrados en el sistema.
    - `serializer_class` transforma los datos en un formato JSON adecuado.
    - `permission_classes` restringe el acceso a usuarios autenticados y administradores.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAdminUser, IsAuthenticated]  # Solo administradores autenticados pueden acceder
