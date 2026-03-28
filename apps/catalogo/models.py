from django.db import models
from apps.escuelas.models import Generacion

# Create your models here.
class Seccion(models.Model):

    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class TamanoProducto(models.Model):

    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre


class Modelo(models.Model):

    nombre = models.CharField(max_length=150)

    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.CASCADE,
        related_name="modelos"
    )

    tamano_producto = models.ForeignKey(
        TamanoProducto,
        on_delete=models.CASCADE,
        related_name="modelos"
    )

    def __str__(self):
        return f"{self.nombre} - {self.tamano_producto.nombre}"


class PrecioBaseGeneracion(models.Model):

    modelo = models.ForeignKey(
        Modelo,
        on_delete=models.CASCADE,
        related_name="precios"
    )

    generacion = models.ForeignKey(
        Generacion,
        on_delete=models.CASCADE
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        unique_together = ("modelo", "generacion")

    def __str__(self):
        return f"{self.modelo.nombre} {self.modelo.seccion}- {self.generacion.anio} - ${self.precio}"
###################### ANILLOS #########################################################3

class Anillo(models.Model):

    modelo = models.CharField(max_length=100)

    metal = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.modelo} - {self.metal}"
    
    
class PrecioAnilloGeneracion(models.Model):

    anillo = models.ForeignKey(
        Anillo,
        on_delete=models.CASCADE
    )

    generacion = models.ForeignKey(
        Generacion,
        on_delete=models.CASCADE
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        unique_together = ("anillo", "generacion")

    def __str__(self):
        return f"{self.anillo.modelo} - {self.generacion.anio} - ${self.precio}"