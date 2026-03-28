# Create your models here.
from django.db import models


class Generacion(models.Model):
    nombre = models.CharField(max_length=50)
    anio = models.IntegerField(unique=True)

    class Meta:
        ordering = ["-anio"]

    def __str__(self):
        return f"Generación {self.anio}"


class Escuela(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.nombre


class Grupo(models.Model):
    nombre = models.CharField(max_length=20)

    escuela = models.ForeignKey(
        Escuela,
        on_delete=models.CASCADE,
        related_name="grupos"
    )

    generacion = models.ForeignKey(
        Generacion,
        on_delete=models.CASCADE,
        related_name="grupos"
    )

    fecha_fotografia = models.DateField(
        null=True,
        blank=True
    )

    hora_fotografia = models.TimeField(
        null=True,
        blank=True
    )

    lugar_fotografia = models.CharField(
        max_length=150,
        blank=True
    )

    class Meta:
        ordering = ["escuela", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "escuela"],
                name="grupo_unico_por_escuela"
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.escuela.nombre} ({self.generacion.anio})"