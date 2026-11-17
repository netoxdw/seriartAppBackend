# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError


class Generacion(models.Model):
    nombre_generacion = models.CharField(max_length=50)
    anio = models.IntegerField(unique=True)

    class Meta:
        ordering = ["-anio"]

    def __str__(self):
        return f"Generación {self.anio}"


class Escuela(models.Model):

    NIVEL_SECUNDARIA = "secundaria"
    NIVEL_PREPARATORIA = "preparatoria"
    NIVEL_UNIVERSIDAD = "universidad"
    NIVEL_OTRO = "otro"
    NIVEL_CHOICES = [
        (NIVEL_SECUNDARIA, "Secundaria"),
        (NIVEL_PREPARATORIA, "Preparatoria"),
        (NIVEL_UNIVERSIDAD, "Universidad"),
        (NIVEL_OTRO, "Otro"),
    ]

    nombre_escuela = models.CharField(max_length=150)
    nivel = models.CharField(
        max_length=20,
        choices=NIVEL_CHOICES,
        default=NIVEL_OTRO,
        help_text="Define qué artículos se precargan en la captura rápida de pedidos."
    )
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    generaciones = models.ManyToManyField(
        Generacion,
        related_name="escuelas"
    )

    def __str__(self):
        return self.nombre_escuela


class Grupo(models.Model):
    nombre_grupo = models.CharField(max_length=20)

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
        ordering = ["escuela", "nombre_grupo"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre_grupo", "escuela", "generacion"],
                name="grupo_unico_por_escuela_generacion"
            )
        ]
    
    def clean(self):
        if self.escuela_id and self.generacion_id:
            if Grupo.objects.filter(
                nombre_grupo=self.nombre_grupo,
                escuela_id=self.escuela_id,
                generacion_id=self.generacion_id
            ).exclude(id=self.id).exists():
                raise ValidationError(
                    "Este grupo ya existe en esta escuela y generación."
                )
    
    def __str__(self):
        escuela = self.escuela.nombre_escuela if self.escuela_id else "Sin escuela"
        generacion = self.generacion.anio if self.generacion_id else "Sin generación"

        return f"{self.nombre_grupo} - {escuela} ({generacion})"