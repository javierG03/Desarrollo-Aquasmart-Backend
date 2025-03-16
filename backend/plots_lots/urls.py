from django.urls import path
from .views import PlotViewSet
urlpatterns = [
    path('register', PlotViewSet.as_view({'post': 'create'}),name='registrar-predio' ),
    # Actualizar un predio 
    path('<int:pk>/update/', PlotViewSet.as_view({'put': 'update', 'patch': 'partial_update'}), name='actualizar-predio'),
]