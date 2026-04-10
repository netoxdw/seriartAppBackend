from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.alumnos.models import Alumno
from apps.catalogo.models import (
    Modelo,
    Anillo,
    PrecioBaseGeneracion,
    PrecioAnilloGeneracion,
)


class Pedido(models.Model):
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name="pedidos"
    )
    fecha = models.DateField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("listo", "Listo para entregar"),
        ("entregado", "Entregado"),
    ]

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="pendiente"
    )
    recibido_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Nombre de la persona que recibe el pedido"
    )

    fecha_entrega = models.DateTimeField(
        blank=True,
        null=True
    )
    
    class Meta:
        ordering = ["-id"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido {self.id} - {self.alumno}"

    def calcular_total(self):
        total_bases = sum(item.subtotal for item in self.items_base.all())
        total_anillos = sum(item.subtotal for item in self.items_anillo.all())
        self.total = total_bases + total_anillos
        self.save(update_fields=["total"])

    def clean(self):
        if self.estado == "entregado":
            if not self.recibido_por:
             raise ValidationError("Debes indicar quién recibió el pedido")
        if not self.fecha_entrega:
            self.fecha_entrega = timezone.now()

    @property
    def total_pagado(self):
        total = self.pagos.aggregate(total=models.Sum("monto"))["total"]
        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        saldo = self.total - self.total_pagado
        return saldo if saldo > 0 else Decimal("0.00")

    @property
    def estado_pago(self):
        if self.total == 0:
            return "Sin pedido"
        if self.total_pagado <= 0:
            return "Pendiente"
        if self.total_pagado < self.total:
            return "Abonando"
        return "Pagado"


class PedidoItemBase(models.Model):

    PLACA_CHOICES = [
        ("mediterranea", "Mediterránea"),
        ("4_piezas", "4 piezas"),
        ("extendida", "Extendida"),
        ("corte_plano", "Corte plano"),
        ("palermo", "Palermo"),
        ("circulo", "Círculo"),
        ("corazon", "Corazón"),
        ("estrella", "Estrella"),
        ("columnas", "Columnas"),
        ("pergamino", "Pergamino"),
    ]

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items_base"
    )

    modelo = models.ForeignKey(
        Modelo,
        on_delete=models.CASCADE,
        related_name="items_pedido_base"
    )

    placa = models.CharField(
        max_length=20,
        choices=PLACA_CHOICES,
        blank=True,
        null=True
    )

    color_placa = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    cantidad = models.PositiveIntegerField(default=1)

    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=0
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=0
    )

    def save(self, *args, **kwargs):
        generacion = self.pedido.alumno.grupo.generacion

        precio_obj = PrecioBaseGeneracion.objects.get(
        modelo=self.modelo,
        generacion=generacion
    )

        self.precio_unitario = precio_obj.precio
        self.subtotal = self.cantidad * self.precio_unitario

        super().save(*args, **kwargs)
        self.pedido.calcular_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.calcular_total()


class PedidoItemAnillo(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items_anillo"
    )
    anillo = models.ForeignKey(
        Anillo,
        on_delete=models.CASCADE,
        related_name="items_pedido_anillo"
    )
    tamano_anillo = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        help_text="Ejemplos: 5, 5.5, 6, 6.5"
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=0
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=0
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Item anillo del pedido"
        verbose_name_plural = "Items anillo del pedido"

    def __str__(self):
        return (
            f"{self.cantidad} - "
            f"{self.anillo.modelo} - "
            f"{self.anillo.metal} - "
            f"Talla {self.tamano_anillo}"
        )

    def save(self, *args, **kwargs):
        generacion = self.pedido.alumno.grupo.generacion

        precio_obj = PrecioAnilloGeneracion.objects.get(
            anillo=self.anillo,
            generacion=generacion
        )

        self.precio_unitario = precio_obj.precio
        self.subtotal = self.cantidad * self.precio_unitario

        super().save(*args, **kwargs)
        self.pedido.calcular_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.calcular_total()


class PedidoItemExtra(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items_extra"
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False
    )

    class Meta:
        verbose_name = "Item Extra"
        verbose_name_plural = "Items Extra"

    def __str__(self):
        return f"{self.nombre} - {self.cantidad} x {self.precio_unitario}"

    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

        # Recalcular total del pedido
        self.pedido.calcular_total()


class Observacion(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="observaciones"
    )
    texto = models.TextField(
        max_length=1000,
        help_text="Detalle u observación del pedido"
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Observación"
        verbose_name_plural = "Observaciones"

    def __str__(self):
        return f"Pedido #{self.pedido.id} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"


class Pago(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="pagos"
    )
    fecha_pago = models.DateField(
        verbose_name="Fecha de emisión del pago"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    folio_nota = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Folio de la nota/recibo"
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago {self.id} - Pedido {self.pedido.id} - ${self.monto}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.monto <= 0:
            raise ValidationError("El monto del pago debe ser mayor a cero.")