from django.db import models
from apps.escuelas.models import Grupo


class Alumno(models.Model):

    nombre = models.CharField(max_length=150)

    telefono = models.CharField(
        max_length=20,
        blank=True
    )

    folio_fotos = models.CharField(
        max_length=100,
        help_text="Folio o folios de las fotos del alumno",
        blank=True
    )

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="alumnos"
    )

    def __str__(self):
        return f"{self.nombre} - {self.grupo.escuela.nombre} {self.grupo.nombre} {self.grupo.generacion}"