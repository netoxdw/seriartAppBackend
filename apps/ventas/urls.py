from django.urls import path
from .views import PedidoCreateView, PedidoDetailView, PedidoItemBaseCreateView, alumno_pedido_redirect, PedidoItemBaseUpdateView, PedidoItemBaseDeleteView

urlpatterns = [
    path('pedidos/nuevo/<int:alumno_id>/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
    path('pedidos/<int:pedido_id>/add-base/', PedidoItemBaseCreateView.as_view(), name='itembase_create'),
    path('alumnos/<int:alumno_id>/pedido/', alumno_pedido_redirect, name='alumno_pedido'),
    path(
        'itembase/<int:pk>/editar/',
        PedidoItemBaseUpdateView.as_view(),
        name='itembase_update'
    ),
    path(
        'itembase/<int:pk>/eliminar/',
        PedidoItemBaseDeleteView.as_view(),
        name='itembase_delete'
    ),
]