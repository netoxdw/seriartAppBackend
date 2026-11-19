"""
Pedidos varios: imprenta, serigrafía y artículos publicitarios
(calendarios, playeras, termos, gorras, reconocimientos...).

Un pedido es de un cliente, tiene uno o más productos capturados a mano,
una fecha de entrega, pagos y un estado.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone


class PedidoVario(models.Model):
    ESTADO_SIN_ANTICIPO = "sin_anticipo"
    ESTADO_HACER = "hacer"
    ESTADO_LISTO = "listo"
    ESTADO_ENTREGADO = "entregado"
    ESTADO_DEVOLUCION = "devolucion"
    ESTADOS = [
        (ESTADO_SIN_ANTICIPO, "Sin anticipo"),
        (ESTADO_HACER, "Hacer"),
        (ESTADO_LISTO, "Listo para entregar"),
        (ESTADO_ENTREGADO, "Entregado"),
        (ESTADO_DEVOLUCION, "Devolución"),
    ]
    # Color de Bootstrap para la etiqueta de cada estado
    COLORES = {
        ESTADO_SIN_ANTICIPO: "danger",
        ESTADO_HACER: "warning",
        ESTADO_LISTO: "primary",
        ESTADO_ENTREGADO: "success",
        ESTADO_DEVOLUCION: "secondary",
    }
    # Estados que todavía cuentan como trabajo pendiente (una devolución hay que rehacerla)
    PENDIENTES = [ESTADO_SIN_ANTICIPO, ESTADO_HACER, ESTADO_LISTO, ESTADO_DEVOLUCION]

    cliente = models.CharField("cliente", max_length=150)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    fecha_entrega = models.DateField("fecha de entrega")
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_SIN_ANTICIPO)
    notas = models.TextField("notas", blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha_entrega", "id"]
        verbose_name = "Pedido vario"
        verbose_name_plural = "Pedidos varios"

    def __str__(self):
        return f"Pedido {self.folio} · {self.cliente}"

    @property
    def folio(self):
        return f"V-{self.pk:04d}" if self.pk else "V-nuevo"

    @property
    def color_estado(self):
        return self.COLORES.get(self.estado, "secondary")

    @property
    def pagado(self):
        return self.pagos.aggregate(s=Sum("monto"))["s"] or Decimal("0")

    @property
    def saldo(self):
        return max(self.total - self.pagado, Decimal("0"))

    @property
    def atrasado(self):
        return self.estado in self.PENDIENTES and self.fecha_entrega < timezone.localdate()

    def calcular_total(self):
        total = self.productos.aggregate(s=Sum(F("cantidad") * F("precio_unitario")))["s"] or Decimal("0")
        PedidoVario.objects.filter(pk=self.pk).update(total=total)
        self.total = total


class ProductoPedidoVario(models.Model):
    pedido = models.ForeignKey(PedidoVario, on_delete=models.CASCADE, related_name="productos")
    producto = models.CharField("producto", max_length=150)
    descripcion = models.TextField("descripción", blank=True)
    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField("precio unitario", max_digits=10, decimal_places=2)
    fecha_elaboracion = models.DateField(
        "elaborar el", null=True, blank=True,
        help_text="Fecha en la que se debe elaborar este producto.",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Producto del pedido"
        verbose_name_plural = "Productos del pedido"

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"

    @property
    def importe(self):
        return (self.cantidad or 0) * (self.precio_unitario or 0)

    def clean(self):
        if self.cantidad is not None and self.cantidad < 1:
            raise ValidationError({"cantidad": "La cantidad debe ser al menos 1."})
        if self.precio_unitario is not None and self.precio_unitario < 0:
            raise ValidationError({"precio_unitario": "El precio no puede ser negativo."})


class PagoPedidoVario(models.Model):
    FORMAS = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("tarjeta", "Tarjeta"),
        ("otro", "Otro"),
    ]

    pedido = models.ForeignKey(PedidoVario, on_delete=models.CASCADE, related_name="pagos")
    fecha = models.DateField("fecha del pago", default=timezone.localdate)
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    forma_pago = models.CharField("forma de pago", max_length=20, choices=FORMAS, default="efectivo")
    referencia = models.CharField("folio / referencia", max_length=60, blank=True)
    registrado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name = "Pago de pedido vario"
        verbose_name_plural = "Pagos de pedidos varios"

    def __str__(self):
        return f"${self.monto} · {self.pedido.folio}"

    def clean(self):
        if self.monto is not None and self.monto <= 0:
            raise ValidationError({"monto": "El monto debe ser mayor a cero."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Con el primer pago (anticipo) el pedido pasa a "Hacer"
        if self.pedido.estado == PedidoVario.ESTADO_SIN_ANTICIPO:
            PedidoVario.objects.filter(pk=self.pedido_id).update(estado=PedidoVario.ESTADO_HACER)
            self.pedido.estado = PedidoVario.ESTADO_HACER
