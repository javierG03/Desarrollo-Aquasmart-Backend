from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from .models import CustomUser, DocumentType, PersonType  
from .serializers import CustomUserSerializer, DocumentTypeSerializer, PersonTypeSerializer ,UserProfileSerializer, UserProfileUpdateSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny  
from drf_spectacular.utils import extend_schema, extend_schema_view,OpenApiParameter
from rest_framework.response import Response
from django.contrib.auth.models import Permission
from .validate import validate_user_exist,is_probably_google_account
from API.google.google_drive import upload_to_drive,share_folder
import os
from django.conf import settings
from .permissions import PuedeCambiarIsActive,CanRegister,CanAddDocumentType
from rest_framework.authentication import TokenAuthentication
from rest_framework import serializers
from django.contrib.auth.models import Group

from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404
from API.sendmsn import send_rejection_email,send_approval_email
@extend_schema_view(
    post=extend_schema(
        summary="Crear un nuevo usuario",
        description="Permite la creación de un nuevo usuario en el sistema.",
        request=CustomUserSerializer,
        responses={201: CustomUserSerializer}
    )
)
class CustomUserCreateView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        # Validar campos inexistentes
        received_fields = set(request.data.keys()) - {'attachments'}
        serializer_fields = set(self.get_serializer().fields.keys())
        invalid_fields = received_fields - serializer_fields

        if invalid_fields:
            return Response(
                {"error": f"Los siguientes campos no existen: {', '.join(invalid_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        uploaded_files = request.FILES.getlist('attachments')
        alert_message = None

        if uploaded_files and user.drive_folder_id:
            for uploaded_file in uploaded_files:
                temp_file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)

                with open(temp_file_path, 'wb+') as temp_file:
                    for chunk in uploaded_file.chunks():
                        temp_file.write(chunk)

                upload_to_drive(temp_file_path, uploaded_file.name, folder_id=user.drive_folder_id)

                try:
                    if is_probably_google_account(user.email):
                        share_folder(folder_id=user.drive_folder_id, email=user.email, role='reader')
                    else:
                        alert_message = f"El correo {user.email} no parece pertenecer a una cuenta de Google."
                except Exception as e:
                    error_msg = str(e)
                    if 'do not have a Google Account' in error_msg:
                        alert_message = f"El correo {user.email} no tiene una cuenta de Google. No se puede compartir la carpeta."
                    else:
                        print(f"Ocurrió un error al compartir la carpeta: {e}")
                        raise Exception(f"Error al compartir la carpeta: {e}")

                os.remove(temp_file_path)

        user.save()

        return Response(
            {
                "message": "Usuario Pre-registrado exitosamente.",
                "user": CustomUserSerializer(user,fields=["document","first_name","last_name","email","drive_folder_id"]).data,
                **({"alert": alert_message} if alert_message else {})
            },
            status=status.HTTP_201_CREATED
        )

    
@extend_schema_view(
    post =extend_schema(
        summary="Crear un nuevo Tipo de documento",
        request=DocumentTypeSerializer,
        responses={201: DocumentTypeSerializer, 403: {"detail": "No tienes permiso para realizar esta acción."}},
        description="Crea un nuevo tipo de documento en el sistema. Requiere permisos de administrador."
))
class DocumentTypeView(generics.CreateAPIView):
    """
    Vista para la creación de tipos de documento.

    Solo los usuarios administradores autenticados pueden acceder a esta vista.
    """

    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [CanAddDocumentType, IsAuthenticated]

class DocumentTypeListView(generics.ListAPIView):
    queryset = DocumentType.objects.all()
    serializer_class= DocumentTypeSerializer
    permission_classes= [AllowAny]    
    
@extend_schema_view(
    post =extend_schema(
    summary="Crear un nuevo Tipo de persona",
    request=PersonTypeSerializer,
    responses={201: PersonTypeSerializer, 403: {"detail": "No tienes permiso para realizar esta acción."}},
    description="Crea un nuevo tipo de persona en el sistema. Requiere permisos de administrador."
))
class PersonTypeView(generics.CreateAPIView):
    """
    Vista para la creación de tipos de persona.

    Solo los usuarios administradores autenticados pueden acceder a esta vista.
    """
    queryset = PersonType.objects.all()
    serializer_class = PersonTypeSerializer
    permission_classes = [IsAdminUser, IsAuthenticated]
    
class PersonTypeListView(generics.ListAPIView):
    queryset = PersonType.objects.all()
    serializer_class= PersonTypeSerializer   
    permission_classes= [AllowAny]       
    
    
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


@extend_schema(
    summary="Registrar usuario",
    description="Activa un usuario desactivado en el sistema. Solo accesible para administradores autenticados.",
    parameters=[
        OpenApiParameter(
            name="document",
            description="Número de documento del usuario a activar",
            required=True,
            type=str,
            location=OpenApiParameter.PATH
        )
    ],
    responses={
        200: {"description": "Usuario activado correctamente.","example":{"status":"User activated"}},
        400: {"description": "El usuario ya está registrado o activado.","example":{"status":"The user is registered or activated."}},
        404: {"description": "Usuario no encontrado.","example":{"error":"User not found."}},
    }
)
class UserRegisterAPIView(APIView):
    """
    API para registar usuario en el sistema.

    Solo los administradores autenticados pueden acceder a esta vista.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,CanRegister]

    def patch(self, request, document):
        """
        Activa un usuario con el número de documento proporcionado.

        Args:
            request: Objeto de la solicitud.
            document (str): Documento del usuario a activar.

        Returns:
            Response: Estado de la activación del usuario.
        """        
        user = validate_user_exist(document)
        name = user.get_full_name()
        send_approval_email(user.email, name)
        # Verificar si ya está registrado
        if user.is_registered:
            return Response({'status': 'el usuario ya se encuentra registrado'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si ya está activo
        if user.is_active:
            return Response({'status': 'El usuario ya se encuentra activo.'}, status=status.HTTP_400_BAD_REQUEST)   
        user.is_registered = True
        user.is_active = True
        user.save()
        group, created = Group.objects.get_or_create(name='Usuario')  # Cambia 'NombreDelGrupo'
        user.groups.add(group)
        return Response({'status': 'User registred'}, status=status.HTTP_200_OK)

class UserInactiveAPIView(APIView):
    """
    API para desactivar usuario en el sistema.

    Solo los administradores autenticados pueden acceder a esta vista.
    """

    permission_classes = [IsAuthenticated, PuedeCambiarIsActive]

    def patch(self, request, document):
        """
        Activa un usuario con el número de documento proporcionado.

        Args:
            request: Objeto de la solicitud.
            document (str): Documento del usuario a activar.

        Returns:
            Response: Estado de la activación del usuario.
        """        
        user = validate_user_exist(document)       
        # Verificar si ya está registrado
        if not user.is_registered:
            return Response({'status': 'El usuario no a pasado el pre-registro o esta pendiente.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si ya está activo
        if not user.is_active:
            return Response({'status': 'El usuario ya se encuentrea inactivo.'}, status=status.HTTP_400_BAD_REQUEST)   
        user.is_active = False
        user.save()
        return Response({'status': 'El usuario a sido desactivado correctamente.'}, status=status.HTTP_200_OK)
    
class UserActivateAPIView(APIView):
    """
    API para activar usuarios en el sistema.

    Solo los administradores autenticados pueden acceder a esta vista.
    """

    permission_classes = [IsAuthenticated, PuedeCambiarIsActive]

    def patch(self, request, document):
        """
        Activa un usuario con el número de documento proporcionado.

        Args:
            request: Objeto de la solicitud.
            document (str): Documento del usuario a activar.

        Returns:
            Response: Estado de la activación del usuario.
        """        
        user = validate_user_exist(document)
       
        # Verificar si ya está registrado
        if not user.is_registered:
            return Response({'status': 'El usuario no a pasado el pre-registro o esta pendiente'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si ya está activo
        if user.is_active:
            return Response({'status': 'El usuario ya se encuentra activo.'}, status=status.HTTP_400_BAD_REQUEST)   
        user.is_active = True
        user.save()
        return Response({'status': 'El usuario a sido activado con exito.'}, status=status.HTTP_200_OK)    

# RF: Actualización de información de usuarios del distrito
@extend_schema_view(
    get=extend_schema(
        summary="Obtener detalles de usuario",
        description="Obtiene información detallada de un usuario específico por documento. Solo para administradores.",
        responses={200: CustomUserSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar usuario",
        description="Actualiza información parcial de un usuario. Solo para superusuarios o administradores.",
        request=CustomUserSerializer,
        responses={200: CustomUserSerializer}
    )
)
class AdminUserUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    API para gestión de actualizaciones de usuarios por administradores
    
    Permite:
    - Ver detalles completos de un usuario (GET)
    - Actualización parcial de campos (PATCH)
    """
    
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    lookup_field = 'document'
    lookup_url_kwarg = 'document'
    
    def get_permissions(self):
        """Define permisos combinados para la vista"""
        return [IsAuthenticated(), self.IsAdminOrSuperUser()]
    
    class IsAdminOrSuperUser(permissions.BasePermission):
        """Permiso personalizado que verifica is_staff o is_superuser"""
        
        def has_permission(self, request, view):
            return request.user.is_staff or request.user.is_superuser
        
        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)
    
    def get_queryset(self):
        """Optimiza consultas relacionadas"""
        return super().get_queryset().select_related('person_type', 'document_type')
    
    def perform_update(self, serializer):
        """Manejo especial para validación de campos y actualización"""
        instance = self.get_object()
        data = self.request.data
        
        # Validar campos inexistentes
        serializer_fields = set(serializer.fields.keys())
        received_fields = set(data.keys())
        invalid_fields = received_fields - serializer_fields
        
        if invalid_fields:
            raise serializers.ValidationError(
                {"error": f"Los siguientes campos no existen: {', '.join(invalid_fields)}"}
            )

        # Verificar si hay cambios reales
        has_changes = any(
            str(getattr(instance, field)) != str(value)
            for field, value in data.items()
            if field in serializer_fields
        )
        
        if not has_changes:
            raise serializers.ValidationError(
                {"error": "No se detectaron cambios en los datos del usuario"}
            )

        # Manejar la contraseña si está presente
        password = serializer.validated_data.pop('password', None)
        instance = serializer.save()
        
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        
        return instance
    
    def patch(self, request, *args, **kwargs):
        """Maneja actualizaciones parciales con formato de respuesta consistente"""
        
        # Validación para el documento
        if 'document' in request.data:
            return Response(
                {
                    'status': 'error',
                    'message': 'Modificación de documento no permitida',
                    'details': 'El documento de identidad no puede ser modificado'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response = super().patch(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            return Response({
                'status': 'success',
                'message': 'Usuario actualizado exitosamente',
                'data': response.data
            }, status=status.HTTP_200_OK)
        
        return response
class UserDetailsView(generics.RetrieveAPIView):
    """
    Vista para obtener el perfil de usuario según el documento proporcionado en la URL.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]  # Requiere autenticación para acceder

    def get_object(self):
        """
        Obtiene el usuario a partir del documento proporcionado en la URL.
        """
        document = self.kwargs.get('document')
        return get_object_or_404(CustomUser, document=document)    

class UserProfilelView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        print(self.request.user)
        return self.request.user
    
class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    queryset = CustomUser.objects.all()

    def get_object(self):
        """Obtiene el usuario actual."""
        return self.request.user  # Asume que el usuario está autenticado

    def update(self, request, *args, **kwargs):
        """Maneja la actualización del perfil del usuario."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class AssignPermissionToUser(APIView):
    permission_classes = [IsAdminUser]  # Solo administradores pueden asignar permisos

    def post(self, request, *args, **kwargs):
        document = request.data.get('document')
        permission_codenames = request.data.get('permission_codenames', [])

        # Validar que se proporcionen los datos necesarios
        if not document or not permission_codenames:
            return Response(
                {"error": "Se requieren document y permission_codenames (lista)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Obtener el usuario por document
            user = CustomUser.objects.get(document=document)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        assigned_permissions = []
        errors = []

        for codename in permission_codenames:
            try:
                # Obtener el permiso
                permission = Permission.objects.get(codename=codename)
                # Asignar el permiso al usuario
                user.user_permissions.add(permission)
                assigned_permissions.append(permission.name)
            except Permission.DoesNotExist:
                errors.append(f"Permiso '{codename}' no encontrado")

        if errors:
            return Response(
                {"message": "Algunos permisos no se asignaron", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": f"Permisos asignados: {', '.join(assigned_permissions)}"},
            status=status.HTTP_200_OK
        )

class RemovePermissionFromUser(APIView):
    permission_classes = [IsAdminUser]  # Solo administradores pueden eliminar permisos

    def post(self, request, *args, **kwargs):
        document = request.data.get('document')
        permission_codenames = request.data.get('permission_codenames', [])

        # Validar que se proporcionen los datos necesarios
        if not document or not permission_codenames:
            return Response(
                {"error": "Se requieren document y permission_codenames (lista)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Obtener el usuario por document
            user = CustomUser.objects.get(document=document)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        removed_permissions = []
        errors = []

        for codename in permission_codenames:
            try:
                # Obtener el permiso
                permission = Permission.objects.get(codename=codename)
                # Eliminar el permiso del usuario
                user.user_permissions.remove(permission)
                removed_permissions.append(permission.name)
            except Permission.DoesNotExist:
                errors.append(f"Permiso '{codename}' no encontrado")

        if errors:
            return Response(
                {"message": "Algunos permisos no se eliminaron", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": f"Permisos eliminados: {', '.join(removed_permissions)}"},
            status=status.HTTP_200_OK
        )


class ListUserPermissions(APIView):
    permission_classes = [IsAdminUser]  # Solo administradores pueden listar permisos

    def get(self, request, document, *args, **kwargs):
        try:
            # Obtener el usuario por document
            user = CustomUser.objects.get(document=document)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Obtener permisos asignados directamente al usuario
        direct_permissions = user.user_permissions.all()
        direct_permissions_list = [perm.codename for perm in direct_permissions]

        # Obtener permisos heredados de grupos
        group_permissions = user.get_group_permissions()
        group_permissions_list = list(group_permissions)

        return Response(
            {
                "direct_permissions": direct_permissions_list,
                "group_permissions": group_permissions_list,
                "all_permissions": list(user.get_all_permissions())
            },
            status=status.HTTP_200_OK
        )
    
class RejectAndDeleteUserView(APIView):
    """
    Vista para rechazar y eliminar un usuario después de enviar un correo de rechazo.
    """
    permission_classes = [IsAuthenticated,IsAdminUser]
    def post(self, request, user_id, format=None):
        try:
            # Obtener el usuario
            user = CustomUser.objects.get(document=user_id)
            email = user.email
            name = user.get_full_name()

            # Obtener el mensaje de rechazo del cuerpo de la solicitud
            mensaje_rechazo = request.data.get('mensaje_rechazo', '')
            if not mensaje_rechazo:
                return Response(
                    {'error': 'El mensaje de rechazo es requerido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Llamar a la función importada para enviar el correo
            resultado_correo = send_rejection_email(email, mensaje_rechazo, name)

            # Eliminar al usuario
            user.delete()

            # Retornar una respuesta exitosa
            return Response(
                {
                    'status': 'success',
                    'message': 'Usuario rechazado y eliminado correctamente.',
                    'email_result': resultado_correo
                },
                status=status.HTTP_200_OK
            )

        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'El usuario no existe.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al procesar la solicitud: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )