from django.urls import path
from . import views

urlpatterns = [
    path('user/bills', views.UserBillListView.as_view(), name='user-bills'),  # Facturas de un usuario
    path('admin/bills', views.AdminBillListView.as_view(), name='admin-bills'),  # Todas las facturas para admin
]
