from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.escuelas.models import Generacion


# =====================================================================
# DIMENSIONES DEL CATÁLOGO
# Cada fila del Excel (TABLA UNICA) = Sección + Modelo + Color + Tamaño
# + Variante. Todas son tablas editables desde el admin.
# =====================================================================

class Seccion(models.Model):
    """Línea de producto: ACANALADA, MOLDURA, DE LUX, CORREDIZA, LIBRO..."""

    nombre = models.CharField(max_length=100, unique=True)
    lleva_placa = models.BooleanField(
        default=False,
        help_text="Si está marcado, los productos de esta sección piden tipo y color de placa.",
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"

    def __str__(self):
        return self.nombre


class Tamano(models.Model):
    """CARTA, DOBLE ESPACIO, ESTANDAR, AMPLIADA, ÚNICO (secciones sin tamaño)..."""

    CONCEPTO_DIPLOMA = "diploma_agradecimiento"
    CONCEPTO_PANORAMICA = "panoramica"
    CONCEPTO_CHOICES = [
        ("", "Sin definir"),
        (CONCEPTO_DIPLOMA, "Diploma / agradecimiento"),
        (CONCEPTO_PANORAMICA, "Foto panorámica"),
    ]

    nombre = models.CharField(max_length=50, unique=True)
    concepto = models.CharField(
        max_length=30, choices=CONCEPTO_CHOICES, blank=True, default="",
        help_text="Qué va en este tamaño; decide las opciones de la captura (columna CONCEPTO del Excel).",
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tamaño"
        verbose_name_plural = "Tamaños"

    def __str__(self):
        return self.nombre


class Modelo(models.Model):
    """Diseño: PIRAMIDAL, ROLEX, ANGULO... Un modelo puede estar en varias secciones."""

    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Color(models.Model):
    """Color del marco: NEGRO, VINO, MIEL, CAOBA..."""

    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "Colores"

    def __str__(self):
        return self.nombre


class Variante(models.Model):
    """ESTANDAR, ESCULTURAS... Puede cambiar el precio."""

    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Placa(models.Model):
    """Tipo de placa: Arena, Mediterránea, Palermo... (antes estaba fijo en el código)."""

    nombre = models.CharField(max_length=50, unique=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


# =====================================================================
# PRODUCTO (una fila del Excel)
# =====================================================================

class Producto(models.Model):
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, related_name="productos")
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="productos")
    tamano = models.ForeignKey(Tamano, on_delete=models.PROTECT, related_name="productos")
    color = models.ForeignKey(
        Color, on_delete=models.PROTECT, related_name="productos", null=True, blank=True
    )
    variante = models.ForeignKey(
        Variante, on_delete=models.PROTECT, related_name="productos", null=True, blank=True
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["seccion__orden", "seccion__nombre", "modelo__nombre", "tamano__orden"]
        constraints = [
            # Nota: en MySQL los NULL no cuentan como iguales en un UNIQUE,
            # por eso clean() también valida los duplicados sin color/variante.
            models.UniqueConstraint(
                fields=["seccion", "modelo", "tamano", "color", "variante"],
                name="producto_unico",
            )
        ]

    def clean(self):
        duplicado = Producto.objects.filter(
            seccion_id=self.seccion_id,
            modelo_id=self.modelo_id,
            tamano_id=self.tamano_id,
            color_id=self.color_id,
            variante_id=self.variante_id,
        ).exclude(pk=self.pk)
        if duplicado.exists():
            raise ValidationError("Ya existe un producto con esa combinación.")

    @property
    def descripcion(self):
        """Texto corto sin la sección ni el tamaño: 'PIRAMIDAL · NEGRO'."""
        partes = [self.modelo.nombre]
        if self.color_id:
            partes.append(self.color.nombre)
        if self.variante_id:
            partes.append(self.variante.nombre)
        return " · ".join(partes)

    def __str__(self):
        return f"{self.seccion} {self.descripcion} - {self.tamano}"

    def precio_para(self, generacion):
        """
        Precio vigente para una generación:
        1. Precio especial del producto, si existe.
        2. Precio por sección + tamaño + variante.
        3. Precio por sección + tamaño (sin variante).
        Devuelve None si no hay precio configurado.
        """
        especial = PrecioEspecial.objects.filter(producto=self, generacion=generacion).first()
        if especial:
            return especial.precio

        base = PrecioBase.objects.filter(
            generacion=generacion, seccion_id=self.seccion_id, tamano_id=self.tamano_id
        )
        if self.variante_id:
            con_variante = base.filter(variante_id=self.variante_id).first()
            if con_variante:
                return con_variante.precio
        sin_variante = base.filter(variante__isnull=True).first()
        return sin_variante.precio if sin_variante else None

    @classmethod
    def con_precio_para(cls, generacion):
        """Productos activos que tienen precio en esa generación (para los formularios)."""
        base = set(
            PrecioBase.objects.filter(generacion=generacion)
            .values_list("seccion_id", "tamano_id", "variante_id")
        )
        especiales = set(
            PrecioEspecial.objects.filter(generacion=generacion)
            .values_list("producto_id", flat=True)
        )
        ids = [
            pid
            for pid, s, t, v in cls.objects.filter(activo=True)
            .values_list("id", "seccion_id", "tamano_id", "variante_id")
            if pid in especiales or (s, t, None) in base or (v and (s, t, v) in base)
        ]
        return cls.objects.filter(id__in=ids)


# =====================================================================
# PRECIOS
# =====================================================================

class PrecioBase(models.Model):
    """Precio por Sección + Tamaño (+ Variante opcional) para una generación."""

    generacion = models.ForeignKey(Generacion, on_delete=models.PROTECT, related_name="precios_base")
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, related_name="precios")
    tamano = models.ForeignKey(Tamano, on_delete=models.PROTECT, related_name="precios")
    variante = models.ForeignKey(
        Variante,
        on_delete=models.PROTECT,
        related_name="precios",
        null=True,
        blank=True,
        help_text="Déjalo vacío si el precio aplica a cualquier variante.",
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-generacion__anio", "seccion__orden", "tamano__orden"]
        verbose_name = "Precio base"
        verbose_name_plural = "Precios base"
        constraints = [
            models.UniqueConstraint(
                fields=["generacion", "seccion", "tamano", "variante"],
                name="precio_base_unico",
            )
        ]

    def clean(self):
        if self.precio is not None and self.precio <= Decimal("0"):
            raise ValidationError("El precio debe ser mayor a cero.")
        duplicado = PrecioBase.objects.filter(
            generacion_id=self.generacion_id,
            seccion_id=self.seccion_id,
            tamano_id=self.tamano_id,
            variante_id=self.variante_id,
        ).exclude(pk=self.pk)
        if duplicado.exists():
            raise ValidationError("Ya existe un precio para esa combinación y generación.")

    def __str__(self):
        variante = f" {self.variante}" if self.variante_id else ""
        return f"{self.seccion} {self.tamano}{variante} ({self.generacion.anio}) - ${self.precio}"


class PrecioEspecial(models.Model):
    """Excepción: un producto concreto con precio distinto al de su sección."""

    generacion = models.ForeignKey(Generacion, on_delete=models.PROTECT, related_name="precios_especiales")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="precios_especiales")
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Precio especial"
        verbose_name_plural = "Precios especiales"
        constraints = [
            models.UniqueConstraint(fields=["generacion", "producto"], name="precio_especial_unico")
        ]

    def clean(self):
        if self.precio is not None and self.precio <= Decimal("0"):
            raise ValidationError("El precio debe ser mayor a cero.")

    def __str__(self):
        return f"{self.producto} ({self.generacion.anio}) - ${self.precio}"


# =====================================================================
# ANILLOS
# =====================================================================

class Anillo(models.Model):
    modelo = models.CharField(max_length=100)
    metal = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["modelo", "metal"]
        constraints = [
            models.UniqueConstraint(fields=["modelo", "metal"], name="anillo_unico")
        ]

    def __str__(self):
        return f"{self.modelo} - {self.metal}"


class PrecioAnilloGeneracion(models.Model):
    anillo = models.ForeignKey(Anillo, on_delete=models.PROTECT, related_name="precios")
    generacion = models.ForeignKey(Generacion, on_delete=models.PROTECT, related_name="precios_anillo")
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Precio de anillo"
        verbose_name_plural = "Precios de anillos"
        constraints = [
            models.UniqueConstraint(fields=["anillo", "generacion"], name="precio_anillo_unico")
        ]

    def __str__(self):
        return f"{self.anillo} ({self.generacion.anio}) - ${self.precio}"
