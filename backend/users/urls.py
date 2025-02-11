from django.urls import path
from .views import CustomUserCreateView, CustomUserListView
from .authentication import  LoginView,RecuperarContraseñaView
urlpatterns = [
    path('users', CustomUserListView.as_view(), name='customuser-list'),  # Listar usuarios
    path('register', CustomUserCreateView.as_view(), name='customuser-create'),  # Crear usuario
    path('login', LoginView.as_view(), name='login'), # Login
    path('recover-password', RecuperarContraseñaView.as_view(), name='recover-password'),
]