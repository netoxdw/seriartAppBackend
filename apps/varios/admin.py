from django.contrib import admin

from .models import PagoPedidoVario, PedidoVario, ProductoPedidoVario


class ProductoInline(admin.TabularInline):
    model = ProductoPedidoVario
    extra = 0


class PagoInline(admin.TabularInline):
    model = PagoPedidoVario
    extra = 0


@admin.register(PedidoVario)
class PedidoVarioAdmin(admin.ModelAdmin):
    list_display = ("folio", "cliente", "telefono", "fecha_entrega", "estado", "total")
    list_filter = ("estado",)
    search_fields = ("cliente", "telefono", "productos__producto")
    inlines = [ProductoInline, PagoInline]
    readonly_fields = ("total",)
