from django.contrib import admin
from .models import Alumno


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre_alumno",
        "telefono",
        "folio_fotos",
        "grupo",
        "get_escuela",
    )

    search_fields = (
        "nombre_alumno",
        "telefono",
        "folio_fotos",
        "grupo__nombre_grupo",
        "grupo__escuela__nombre_escuela",
    )

    list_filter = (
        "grupo__escuela",
        "grupo",
    )

    ordering = ("nombre_alumno",)

    def get_escuela(self, obj):
        return obj.grupo.escuela

    get_escuela.short_description = "Escuela"