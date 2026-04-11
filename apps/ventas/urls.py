from django.urls import path
from .views import PedidoCreateView, PedidoDetailView

urlpatterns = [
    path('pedidos/nuevo/<int:alumno_id>/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
]