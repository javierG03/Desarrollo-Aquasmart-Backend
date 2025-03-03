from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    document = serializers.CharField(max_length=12)
    password = serializers.CharField(max_length=128)

class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()