from django.urls import path
from .views import (
    PedidoCreateView,
    PedidoDetailView,
    PedidoItemBaseCreateView, 
    alumno_pedido_redirect, 
    PedidoItemBaseUpdateView, 
    PedidoItemBaseDeleteView, 
    PedidoItemAnilloCreateView,
    PedidoItemAnilloUpdateView,
    PedidoItemAnilloDeleteView,
    PedidoItemExtraCreateView,
    PedidoItemExtraUpdateView,
    PedidoItemExtraDeleteView,
    ObservacionCreateView,
    ObservacionUpdateView,
    ObservacionDeleteView
    )

urlpatterns = [
    path('pedidos/nuevo/<int:alumno_id>/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),


    path('pedidos/<int:pedido_id>/add-base/', PedidoItemBaseCreateView.as_view(), name='itembase_create'),
    path('alumnos/<int:alumno_id>/pedido/', alumno_pedido_redirect, name='alumno_pedido'),
    path('itembase/<int:pk>/editar/', PedidoItemBaseUpdateView.as_view(), name='itembase_update'),
    path('itembase/<int:pk>/eliminar/', PedidoItemBaseDeleteView.as_view(), name='itembase_delete'),

    path('pedidos/<int:pedido_id>/add-anillo/', PedidoItemAnilloCreateView.as_view(), name='itemanillo_create'),
    path('itemanillo/<int:pk>/editar/', PedidoItemAnilloUpdateView.as_view(), name='itemanillo_update'),
    path('itemanillo/<int:pk>/eliminar/', PedidoItemAnilloDeleteView.as_view(), name='itemanillo_delete'),

    path('pedidos/<int:pedido_id>/add-extra/', PedidoItemExtraCreateView.as_view(), name='itemextra_create'),
    path('itemextra/<int:pk>/editar/', PedidoItemExtraUpdateView.as_view(), name='itemextra_update'),
    path('itemextra/<int:pk>/eliminar/', PedidoItemExtraDeleteView.as_view(), name='itemextra_delete'),

    path('pedidos/<int:pedido_id>/add-observacion/', ObservacionCreateView.as_view(), name='observacion_create'),
    path('observacion/<int:pk>/editar/', ObservacionUpdateView.as_view(), name='observacion_update'),
    path('observacion/<int:pk>/eliminar/', ObservacionDeleteView.as_view(), name='observacion_delete'),
]