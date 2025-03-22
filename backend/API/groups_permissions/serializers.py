from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "app_label", "model"]


class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class ContentTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()  # Campo personalizado para el nombre legible

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'name']

    def get_name(self, obj):
        # Formato: "app_label | model"
        return f"{obj.app_label} | {obj.model}" 
        
class GroupPermissionSerializer(serializers.ModelSerializer):
    group_names = serializers.SerializerMethodField()
    content_type = serializers.CharField(source='content_type.name')  # Usar el campo personalizado

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type', 'group_names']

    def get_group_names(self, obj):
        # Obtener los nombres de todos los grupos a los que pertenece el permiso
        return list(obj.group_set.values_list('name', flat=True))