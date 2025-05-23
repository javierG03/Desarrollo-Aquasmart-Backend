from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from users.models import CustomUser
class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    model = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'app_label', 'model']        

class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class ContentTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()


    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'name']

    def get_name(self, obj):
        # Formato: "app_label | model"
        return f"{obj.app_label} | {obj.model}"
        
class GroupPermissionSerializer(serializers.ModelSerializer):
    content_type = ContentTypeSerializer()

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']

class UsersGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['document', 'first_name','email']