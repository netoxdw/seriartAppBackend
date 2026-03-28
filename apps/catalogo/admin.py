from django.contrib import admin
from .models import (
    Seccion,
    TamanoProducto,
    Modelo,
    PrecioBaseGeneracion,
    Anillo,
    PrecioAnilloGeneracion
)


@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):

    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(TamanoProducto)
class TamanoProductoAdmin(admin.ModelAdmin):

    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):

    list_display = ("nombre", "seccion", "tamano_producto")
    list_filter = ("seccion", "tamano_producto")
    search_fields = ("nombre",)



@admin.register(PrecioBaseGeneracion)
class PrecioBaseGeneracionAdmin(admin.ModelAdmin):

    list_display = (
        "modelo",
        "tamano_producto",
        "seccion",
        "generacion",
        "precio",
    )

    list_filter = (
        "generacion",
        "modelo__seccion",
        "modelo__tamano_producto",
    )

    search_fields = (
        "modelo__nombre",
    )

    def tamano_producto(self, obj):
        return obj.modelo.tamano_producto

    tamano_producto.short_description = "Tamaño"

    def seccion(self, obj):
        return obj.modelo.seccion

    seccion.short_description = "Sección"


@admin.register(Anillo)
class AnilloAdmin(admin.ModelAdmin):

    list_display = ("modelo", "metal")
    list_filter = ("metal",)
    search_fields = ("modelo",)


@admin.register(PrecioAnilloGeneracion)
class PrecioAnilloGeneracionAdmin(admin.ModelAdmin):

    list_display = ("anillo", "generacion", "precio")

    list_filter = ("generacion",)

    search_fields = ("anillo__nombre",)