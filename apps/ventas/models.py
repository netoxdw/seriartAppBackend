from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.alumnos.models import Alumno
from apps.catalogo.models import (
    Producto,
    Placa,
    Anillo,
    PrecioAnilloGeneracion,
)

# PEDIDO


class TransicionInvalida(ValidationError):
    """El cambio de estado no está permitido desde el estado actual."""


class Pedido(models.Model):

    # --- Estados automáticos (dependen del anticipo pagado) ---
    SIN_ANTICIPO = "sin_anticipo"
    POCO_ANTICIPO = "poco_anticipo"
    HACER = "hacer"
    # --- Estados que registra el staff ---
    LISTO = "listo"
    ENTREGADO = "entregado"
    DEVOLUCION = "devolucion"

    ESTADO_CHOICES = [
        (SIN_ANTICIPO, "Sin anticipo"),
        (POCO_ANTICIPO, "Poco anticipo"),
        (HACER, "Hacer"),
        (LISTO, "Listo para entregar"),
        (ENTREGADO, "Entregado"),
        (DEVOLUCION, "Devolución"),
    ]
    ESTADOS_AUTOMATICOS = (SIN_ANTICIPO, POCO_ANTICIPO, HACER)
    # Porcentaje del total pagado a partir del cual el pedido pasa a "Hacer"
    PORCENTAJE_HACER = Decimal("50")

    COLORES_ESTADO = {
        SIN_ANTICIPO: "secondary",
        POCO_ANTICIPO: "warning",
        HACER: "primary",
        LISTO: "info",
        ENTREGADO: "success",
        DEVOLUCION: "danger",
    }

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name="pedidos"
    )

    fecha = models.DateField(
        auto_now_add=True
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=SIN_ANTICIPO,
        db_index=True
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

    actualizado = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True
    )

    notas_entrega = models.TextField(
        blank=True,
        null=True
    )

    motivo_devolucion = models.TextField(
        blank=True,
        null=True,
        help_text="Motivo de la última devolución (el historial guarda todas)."
    )

    fecha_devolucion = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido {self.id} - {self.alumno}"

    @property
    def entregado(self):
        return self.estado == self.ENTREGADO

    @property
    def color_estado(self):
        return self.COLORES_ESTADO.get(self.estado, "secondary")

    # ------------------------------------------------------------------
    # Totales y pagos
    # ------------------------------------------------------------------

    def calcular_total(self):
        total_bases = sum(item.subtotal for item in self.items_base.all())
        total_anillos = sum(item.subtotal for item in self.items_anillo.all())
        total_extras = sum(item.subtotal for item in self.items_extra.all())
        total_descuentos = sum(d.monto for d in self.descuentos.all())

        self.total = total_bases + total_anillos + total_extras - total_descuentos

        # 🔥 evitar negativos
        if self.total < 0:
            self.total = 0

        self.save(update_fields=["total"])
        # El total o los pagos cambiaron: el estado por anticipo puede cambiar
        self.actualizar_estado_por_anticipo()

    def clean(self):
        if self.estado == self.ENTREGADO and not self.recibido_por:
            raise ValidationError("Debes indicar quién recibió el pedido.")
        if self.estado == self.DEVOLUCION and not (self.motivo_devolucion or "").strip():
            raise ValidationError("Debes indicar el motivo de la devolución.")

    @property
    def total_pagado(self):
        total = self.pagos.aggregate(total=models.Sum("monto"))["total"]
        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        saldo = self.total - self.total_pagado
        return saldo if saldo > 0 else Decimal("0.00")

    @property
    def porcentaje_pagado(self):
        if self.total <= 0:
            return Decimal("0")
        return (self.total_pagado * 100 / self.total).quantize(Decimal("0.1"))

    @property
    def estado_pago(self):
        if self.total == 0:
            return "Sin pedido"
        if self.total_pagado <= 0:
            return "Pendiente"
        if self.total_pagado < self.total:
            return "Abonando"
        return "Pagado"

    # ------------------------------------------------------------------
    # Estados
    # ------------------------------------------------------------------

    def estado_por_anticipo(self):
        """Sin anticipo / Poco anticipo (< 50 %) / Hacer (>= 50 %)."""
        pagado = self.total_pagado
        if pagado <= 0:
            return self.SIN_ANTICIPO
        if self.total > 0 and pagado * 100 < self.total * self.PORCENTAJE_HACER:
            return self.POCO_ANTICIPO
        return self.HACER

    @property
    def anticipo_suficiente(self):
        return self.estado_por_anticipo() == self.HACER

    def _registrar(self, anterior, usuario=None, nota=""):
        PedidoEstadoHistorial.objects.create(
            pedido=self,
            estado_anterior=anterior,
            estado_nuevo=self.estado,
            usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
            nota=nota or "",
        )

    def actualizar_estado_por_anticipo(self):
        """Solo mueve el estado mientras el pedido está en un estado automático."""
        if self.estado not in self.ESTADOS_AUTOMATICOS:
            return False
        nuevo = self.estado_por_anticipo()
        if nuevo == self.estado:
            return False
        anterior = self.estado
        self.estado = nuevo
        self.save(update_fields=["estado", "actualizado"])
        self._registrar(anterior, nota="Cambio automático por anticipo")
        return True

    def _exigir(self, permitidos, accion):
        if self.estado not in permitidos:
            raise TransicionInvalida(
                f"No se puede {accion} un pedido en estado «{self.get_estado_display()}»."
            )

    @property
    def listo_tras_devolucion(self):
        """True si el pedido está «Listo» porque se corrigió después de una devolución."""
        if self.estado != self.LISTO:
            return False
        ultimo = (
            self.historial_estados.filter(estado_nuevo=self.LISTO)
            .order_by("-fecha", "-id")
            .first()
        )
        return bool(ultimo and ultimo.estado_anterior == self.DEVOLUCION)

    def marcar_listo(self, usuario, nota=""):
        # Desde producción, o desde una devolución ya corregida (para volver a entregar)
        self._exigir(self.ESTADOS_AUTOMATICOS + (self.DEVOLUCION,), "marcar como listo")
        anterior = self.estado
        self.estado = self.LISTO
        self.save(update_fields=["estado", "actualizado"])
        if anterior == self.DEVOLUCION:
            nota = "Corregido tras devolución" + (f". {nota}" if nota else "")
        self._registrar(anterior, usuario, nota)

    def regresar_a_produccion(self, usuario, nota=""):
        """Deshace «Listo»: vuelve a Devolución si de ahí venía; si no, al estado según anticipo."""
        self._exigir((self.LISTO,), "regresar a producción")
        tras_devolucion = self.listo_tras_devolucion
        anterior = self.estado
        self.estado = self.DEVOLUCION if tras_devolucion else self.estado_por_anticipo()
        self.save(update_fields=["estado", "actualizado"])
        self._registrar(anterior, usuario, nota or "Se deshizo 'Listo para entregar'")

    def marcar_entregado(self, usuario, recibido_por, nota=""):
        self._exigir((self.LISTO, self.DEVOLUCION), "marcar como entregado")
        reentrega = self.estado == self.DEVOLUCION or self.listo_tras_devolucion
        recibido_por = (recibido_por or "").strip()
        if not recibido_por:
            raise ValidationError("Debes indicar quién recibe el pedido.")
        anterior = self.estado
        self.estado = self.ENTREGADO
        self.recibido_por = recibido_por
        self.fecha_entrega = timezone.now()
        if nota:
            self.notas_entrega = nota
        self.save(update_fields=["estado", "recibido_por", "fecha_entrega", "notas_entrega", "actualizado"])
        texto = f"Recibió: {recibido_por}" + (f". {nota}" if nota else "")
        if reentrega:
            texto = "Reentrega tras devolución. " + texto
        self._registrar(anterior, usuario, texto)

    def marcar_devuelto(self, usuario, motivo):
        self._exigir((self.ENTREGADO,), "registrar la devolución de")
        motivo = (motivo or "").strip()
        if not motivo:
            raise ValidationError("Debes indicar el motivo de la devolución.")
        anterior = self.estado
        self.estado = self.DEVOLUCION
        self.motivo_devolucion = motivo
        self.fecha_devolucion = timezone.now()
        self.save(update_fields=["estado", "motivo_devolucion", "fecha_devolucion", "actualizado"])
        self._registrar(anterior, usuario, motivo)


class PedidoEstadoHistorial(models.Model):
    """Cada cambio de estado de un pedido: quién, cuándo y por qué."""

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="historial_estados"
    )
    estado_anterior = models.CharField(max_length=20, choices=Pedido.ESTADO_CHOICES, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=Pedido.ESTADO_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cambios_estado_pedido",
        help_text="Vacío = cambio automático del sistema."
    )
    fecha = models.DateTimeField(auto_now_add=True)
    nota = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Cambio de estado"
        verbose_name_plural = "Historial de estados"

    def __str__(self):
        return f"Pedido {self.pedido_id}: {self.estado_anterior} → {self.estado_nuevo}"


# BASES

class PedidoItemBase(models.Model):

    CONCEPTO_PANORAMICA = "panoramica"
    CONCEPTO_DIPLOMA = "diploma"
    CONCEPTO_AGRADECIMIENTO = "agradecimiento"
    CONCEPTO_OTRO = "otro"
    CONCEPTO_CHOICES = [
        (CONCEPTO_PANORAMICA, "Foto panorámica"),
        (CONCEPTO_DIPLOMA, "Diploma"),
        (CONCEPTO_AGRADECIMIENTO, "Agradecimiento"),
        (CONCEPTO_OTRO, "Otro"),
    ]

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items_base"
    )

    concepto = models.CharField(
        max_length=20,
        choices=CONCEPTO_CHOICES,
        default=CONCEPTO_OTRO,
        help_text="Qué va en el marco: foto panorámica, diploma, agradecimiento u otro."
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="items_pedido"
    )

    placa = models.ForeignKey(
        Placa,
        on_delete=models.PROTECT,
        related_name="items_pedido",
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

    class Meta:
        ordering = ["id"]
        verbose_name = "Item base del pedido"
        verbose_name_plural = "Items base del pedido"

    def __str__(self):
        return f"{self.cantidad} x {self.producto}"

    def _precio_catalogo(self):
        generacion = self.pedido.alumno.grupo.generacion
        return self.producto.precio_para(generacion)

    def clean(self):
        if self.producto_id and self.pedido_id:
            if self._state.adding or self._producto_cambio():
                if self._precio_catalogo() is None:
                    raise ValidationError(
                        "Este producto no tiene precio para la generación del alumno."
                    )
            if not self.producto.seccion.lleva_placa:
                self.placa = None
                self.color_placa = None

    def _producto_cambio(self):
        anterior = (
            PedidoItemBase.objects.filter(pk=self.pk)
            .values_list("producto_id", flat=True)
            .first()
        )
        return anterior != self.producto_id

    def save(self, *args, **kwargs):
        # El precio se toma del catálogo solo al crear el ítem o al cambiar
        # de producto; editar la cantidad conserva el precio original.
        if self._state.adding or self._producto_cambio():
            precio = self._precio_catalogo()
            if precio is None:
                raise ValidationError(
                    "Este producto no tiene precio para la generación del alumno."
                )
            self.precio_unitario = precio

        self.subtotal = self.cantidad * self.precio_unitario

        super().save(*args, **kwargs)
        self.pedido.calcular_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.calcular_total()

# ANILLO

class PedidoItemAnillo(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items_anillo"
    )
    anillo = models.ForeignKey(
        Anillo,
        on_delete=models.PROTECT,
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

# EXTRA

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
        # 🔥 Calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

        # 🔥 Recalcular total del pedido
        self.pedido.calcular_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido  # 🔥 guardar referencia antes de borrar
        super().delete(*args, **kwargs)

        # 🔥 Recalcular total después de eliminar
        pedido.calcular_total()


# OBSERVACION

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

# PAGOS

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.pedido.calcular_total()  # 🔥 clave

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.calcular_total()  # 🔥 clave

# DESCUENTO

class PedidoDescuento(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="descuentos"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    motivo = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Descuento"
        verbose_name_plural = "Descuentos"

    def __str__(self):
        return f"Descuento ${self.monto} - Pedido {self.pedido.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.pedido.calcular_total()

    def clean(self):
        if self.monto <= 0:
            raise ValidationError("El descuento debe ser mayor a cero.")

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.calcular_total()