from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("precios/", views.precios, name="precios"),
    path("productos/", views.productos, name="productos"),
    path("productos/nuevo/", views.producto_alta, name="producto_alta"),
    path("anillos/", views.anillos, name="anillos"),
    path("dimensiones/", views.dimensiones, name="dimensiones_inicio"),
    path("dimensiones/<slug:tipo>/", views.dimensiones, name="dimensiones"),
    path("copiar-precios/", views.copiar_precios, name="copiar_precios"),
    path("importar/", views.importar, name="importar"),
]
