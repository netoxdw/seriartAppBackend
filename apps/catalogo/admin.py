from django.contrib import admin
from import_export.admin import ExportMixin

from .models import (
    Anillo,
    Color,
    Modelo,
    Placa,
    PrecioAnilloGeneracion,
    PrecioBase,
    PrecioEspecial,
    Producto,
    Seccion,
    Tamano,
    Variante,
)

# El catálogo completo se carga desde el Excel con:
#   python manage.py importar_catalogo catalogo_seriart.xlsx --generacion 2027


@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "lleva_placa", "orden", "activo")
    list_editable = ("lleva_placa", "orden", "activo")
    search_fields = ("nombre",)


@admin.register(Tamano)
class TamanoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)


@admin.register(Modelo, Color, Variante)
class DimensionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_editable = ("activo",)
    search_fields = ("nombre",)


@admin.register(Placa)
class PlacaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("seccion", "modelo", "color", "tamano", "variante", "activo")
    list_editable = ("activo",)
    list_filter = ("seccion", "tamano", "color", "variante", "activo")
    search_fields = ("modelo__nombre", "seccion__nombre")
    list_select_related = ("seccion", "modelo", "color", "tamano", "variante")
    autocomplete_fields = ("modelo",)


@admin.register(PrecioBase)
class PrecioBaseAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("generacion", "seccion", "tamano", "variante", "precio")
    list_editable = ("precio",)
    list_filter = ("generacion", "seccion", "tamano")
    list_select_related = ("generacion", "seccion", "tamano", "variante")


@admin.register(PrecioEspecial)
class PrecioEspecialAdmin(admin.ModelAdmin):
    list_display = ("generacion", "producto", "precio")
    list_editable = ("precio",)
    list_filter = ("generacion",)
    autocomplete_fields = ("producto",)


class PrecioAnilloInline(admin.TabularInline):
    model = PrecioAnilloGeneracion
    extra = 1


@admin.register(Anillo)
class AnilloAdmin(admin.ModelAdmin):
    list_display = ("modelo", "metal", "activo")
    list_editable = ("activo",)
    list_filter = ("metal", "activo")
    search_fields = ("modelo", "metal")
    inlines = [PrecioAnilloInline]


@admin.register(PrecioAnilloGeneracion)
class PrecioAnilloGeneracionAdmin(admin.ModelAdmin):
    list_display = ("anillo", "generacion", "precio")
    list_editable = ("precio",)
    list_filter = ("generacion",)
    search_fields = ("anillo__modelo", "anillo__metal")
