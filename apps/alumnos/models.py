from django.db import models
from apps.escuelas.models import Grupo


class Alumno(models.Model):

    nombre_alumno = models.CharField(max_length=150)

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nombre_alumno", "grupo"],
                name="alumno_unico_por_grupo"
            )
        ]

    def __str__(self):
        return f"{self.nombre_alumno} - {self.grupo.escuela.nombre_escuela} {self.grupo.nombre_grupo} {self.grupo.generacion}"