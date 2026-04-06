from django.contrib import admin
from .models import Generacion, Escuela, Grupo


admin.site.register(Generacion)

from django.contrib import admin
from .models import Escuela


@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "direccion",
        "telefono",
        "get_generaciones",
    )

    search_fields = (
        "nombre",
        "direccion",
        "telefono",
    )

    list_filter = (
        "generaciones",
    )

    filter_horizontal = ("generaciones",)

    def get_generaciones(self, obj):
        return ", ".join([str(g.anio) for g in obj.generaciones.all()])

    get_generaciones.short_description = "Generaciones"

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "escuela",
        "generacion",
    )

    search_fields = (
        "nombre",
        "escuela__nombre",
    )

    list_filter = (
        "escuela",
        "generacion",
    )