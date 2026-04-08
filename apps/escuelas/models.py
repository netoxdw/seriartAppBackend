# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError


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

    generaciones = models.ManyToManyField(
        Generacion,
        related_name="escuelas"
    )

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
                fields=["nombre", "escuela", "generacion"],
                name="grupo_unico_por_escuela_generacion"
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.escuela.nombre} ({self.generacion.anio})"
    
    def clean(self):
        if self.escuela_id and self.generacion_id:
            if Grupo.objects.filter(
                nombre=self.nombre,
                escuela_id=self.escuela_id,
                generacion_id=self.generacion_id
            ).exclude(id=self.id).exists():
                raise ValidationError(
                    "Este grupo ya existe en esta escuela y generación."
                )