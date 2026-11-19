from django.urls import path

from . import views

app_name = "varios"

urlpatterns = [
    path("", views.pedido_list, name="pedido_list"),
    path("nuevo/", views.pedido_create, name="pedido_create"),
    path("<int:pk>/", views.pedido_detail, name="pedido_detail"),
    path("<int:pk>/editar/", views.pedido_update, name="pedido_update"),
    path("<int:pk>/estado/", views.pedido_estado, name="pedido_estado"),
    path("<int:pk>/eliminar/", views.pedido_delete, name="pedido_delete"),
    path("<int:pk>/pago/", views.pago_create, name="pago_create"),
    path("pago/<int:pk>/eliminar/", views.pago_delete, name="pago_delete"),
]
