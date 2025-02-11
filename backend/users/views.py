from rest_framework import generics,status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import CustomUser  
from .serializers import CustomUserSerializer  
from rest_framework.permissions import IsAdminUser, IsAuthenticated  
from drf_spectacular.utils import extend_schema, extend_schema_view,OpenApiParameter
from rest_framework.response import Response
@extend_schema_view(
    post=extend_schema(
        summary="Crear un nuevo usuario",
        description="Permite la creación de un nuevo usuario en el sistema.",
        request=CustomUserSerializer,
        responses={201: CustomUserSerializer}
    )
)
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
    
    
@extend_schema_view(
    get=extend_schema(
        summary="Listar todos los usuarios",
        description="Devuelve una lista de todos los usuarios registrados. "
                    "Solo accesible para administradores autenticados.",
        responses={200: CustomUserSerializer(many=True)}
    )
)
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


class UserRegisterAPIView(APIView):
    """
    API para la activación de usuarios.

    Permite que un administrador active un usuario estableciendo los campos `isRegistered` 
    e `is_active` en `True`.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary="Activar un usuario",
        description="Activa un usuario cambiando los campos `isRegistered` y `is_active` a `True`. "
                    "Solo accesible para administradores autenticados.",
        parameters=[
            OpenApiParameter(
                name="document",
                type=str,
                location=OpenApiParameter.PATH,
                required=True,
                description="Número de documento del usuario a activar"
            )
        ],
        responses={
            200: {"description": "Usuario activado con éxito", "example": {"status": "User activated"}},
            404: {"description": "Usuario no encontrado", "example": {"detail": "Not found."}}
        }
    )
    def patch(self, request, document):
        """
        Activa un usuario en el sistema.

        Parámetros:
        - request: La solicitud HTTP con los datos del cliente.
        - document: Número de documento del usuario que se desea activar.
        """
        user = get_object_or_404(CustomUser, document=document)
        user.isRegistered = True
        user.is_active = True
        user.save()
        return Response({'status': 'User activated'}, status=status.HTTP_200_OK)
