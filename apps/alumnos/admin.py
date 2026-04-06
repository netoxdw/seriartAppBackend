from django.contrib import admin
from .models import Alumno


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "telefono",
        "folio_fotos",
        "grupo",
        "get_escuela",
    )

    search_fields = (
        "nombre",
        "telefono",
        "folio_fotos",
        "grupo__nombre",
        "grupo__escuela__nombre",
    )

    list_filter = (
        "grupo__escuela",
        "grupo",
    )

    ordering = ("nombre",)

    def get_escuela(self, obj):
        return obj.grupo.escuela

    get_escuela.short_description = "Escuela"