from django.contrib import admin
from .models import Pedido, PedidoItemBase, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento
from django.utils.html import format_html

class PedidoItemBaseInline(admin.TabularInline):
    model = PedidoItemBase
    extra = 1
    fields = (
        "get_tamano",
        "get_seccion",
        "modelo",
        "placa",
        "color_placa",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    readonly_fields = (
        "get_tamano",
        "get_seccion",
        "precio_unitario",
        "subtotal",
    )

    def get_tamano(self, obj):
        if obj and obj.modelo:
            return obj.modelo.tamano_producto
        return "-"
    get_tamano.short_description = "Tamaño"

    def get_seccion(self, obj):
        if obj and obj.modelo:
            return obj.modelo.seccion
        return "-"
    get_seccion.short_description = "Sección"


class PedidoItemAnilloInline(admin.TabularInline):
    model = PedidoItemAnillo
    extra = 0
    fields = (
        "get_modelo",
        "get_metal",
        "anillo",
        "tamano_anillo",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    readonly_fields = (
        "get_modelo",
        "get_metal",
        "precio_unitario",
        "subtotal",
    )

    def get_modelo(self, obj):
        if obj and obj.anillo:
            return obj.anillo.modelo
        return "-"
    get_modelo.short_description = "Modelo"

    def get_metal(self, obj):
        if obj and obj.anillo:
            return obj.anillo.metal
        return "-"
    get_metal.short_description = "Metal"


class PedidoItemExtraInline(admin.TabularInline):
    model = PedidoItemExtra
    extra = 1
    fields = (
        "nombre",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    readonly_fields = ("subtotal",)


class ObservacionInline(admin.TabularInline):
    model = Observacion
    extra = 1
    fields = ("texto", "fecha")
    readonly_fields = ("fecha",)


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 1
    fields = ("fecha_pago", "monto", "folio_nota")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "alumno",
        "fecha",
        "estado_color",
        "total",
        "mostrar_total_pagado",
        "mostrar_saldo_pendiente",
        "mostrar_estado_pago",
        "recibido_por",
        "fecha_entrega",
    )

    search_fields = (
        "id",
        "alumno__nombre",
        "alumno__telefono",
        "recibido_por",
    )

    list_filter = (
        "estado",
        "fecha",
        "fecha_entrega",
    )

    readonly_fields = (
        "total",
        "mostrar_total_pagado",
        "mostrar_saldo_pendiente",
        "mostrar_estado_pago",
        "fecha_entrega",
        "actualizado",
    )

    inlines = [
        PedidoItemBaseInline,
        PedidoItemAnilloInline,
        PedidoItemExtraInline,
        ObservacionInline,
        PagoInline,
    ]

    ordering = ("-id",)

    list_per_page = 25

    # =========================
    # ESTADO CON COLOR
    # =========================

    def estado_color(self, obj):

        colores = {
            "pendiente": "#ffc107",
            "proceso": "#0d6efd",
            "listo": "#198754",
            "entregado": "#6c757d",
        }

        return format_html(
            """
            <span style="
                background-color: {};
                color: white;
                padding: 5px 10px;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 600;
            ">
                {}
            </span>
            """,
            colores.get(obj.estado, "#6c757d"),
            obj.get_estado_display()
        )

    estado_color.short_description = "Estado"

    # =========================
    # PAGOS
    # =========================

    def mostrar_total_pagado(self, obj):
        return obj.total_pagado

    mostrar_total_pagado.short_description = "Total pagado"

    def mostrar_saldo_pendiente(self, obj):
        return obj.saldo_pendiente

    mostrar_saldo_pendiente.short_description = "Saldo pendiente"

    def mostrar_estado_pago(self, obj):
        return obj.estado_pago

    mostrar_estado_pago.short_description = "Estado de pago"


@admin.register(PedidoItemBase)
class PedidoItemBaseAdmin(admin.ModelAdmin):
    list_display = (
        "pedido",
        "mostrar_tamano",
        "mostrar_seccion",
        "mostrar_modelo",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    list_filter = (
        "modelo__tamano_producto",
        "modelo__seccion",
    )
    search_fields = (
        "pedido__alumno__nombre",
        "modelo__nombre",
    )
    readonly_fields = ("precio_unitario", "subtotal")

    def mostrar_tamano(self, obj):
        return obj.modelo.tamano_producto
    mostrar_tamano.short_description = "Tamaño"

    def mostrar_seccion(self, obj):
        return obj.modelo.seccion
    mostrar_seccion.short_description = "Sección"

    def mostrar_modelo(self, obj):
        return obj.modelo.nombre
    mostrar_modelo.short_description = "Modelo"


@admin.register(PedidoItemAnillo)
class PedidoItemAnilloAdmin(admin.ModelAdmin):
    list_display = (
        "pedido",
        "mostrar_modelo",
        "mostrar_metal",
        "tamano_anillo",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    list_filter = (
        "anillo__modelo",
        "anillo__metal",
    )
    search_fields = (
        "pedido__alumno__nombre",
        "anillo__modelo",
        "anillo__metal",
    )
    readonly_fields = ("precio_unitario", "subtotal")

    def mostrar_modelo(self, obj):
        return obj.anillo.modelo
    mostrar_modelo.short_description = "Modelo"

    def mostrar_metal(self, obj):
        return obj.anillo.metal
    mostrar_metal.short_description = "Metal"


@admin.register(PedidoItemExtra)
class PedidoItemExtraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "nombre",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    search_fields = (
        "nombre",
        "pedido__alumno__nombre",
    )
    list_filter = ("pedido",)
    readonly_fields = ("subtotal",)
    ordering = ("-id",)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "fecha_pago",
        "fecha_registro",
        "monto",
        "folio_nota",
    )
    list_filter = ("fecha_pago", "fecha_registro")
    search_fields = (
        "pedido__alumno__nombre",
        "folio_nota",
    )
    readonly_fields = ("fecha_registro",)

# DESCUENTO

# apps/ventas/admin.py

@admin.register(PedidoDescuento)
class PedidoDescuentoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "monto", "motivo", "fecha")


