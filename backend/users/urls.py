from django.urls import path
from .views import CustomUserCreateView, CustomUserListView,UserRegisterAPIView
from .authentication import  LoginView,RecoverPasswordView
urlpatterns = [
    path('users', CustomUserListView.as_view(), name='customuser-list'),  # Listar usuarios
    path('pre-register', CustomUserCreateView.as_view(), name='customuser-pre-register'),  # Pre-registro de usuarios
    path("register/<str:document>", UserRegisterAPIView.as_view(), name='customuser-register'),
    path('login', LoginView.as_view(), name='login'), # Login
    path('recover-password', RecoverPasswordView.as_view(), name='recover-password'),
]