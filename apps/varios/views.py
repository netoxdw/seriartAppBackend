from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PagoForm, PedidoVarioForm, ProductoFormSet
from .models import PagoPedidoVario, PedidoVario


def _con_pagado(qs):
    pagos = (
        PagoPedidoVario.objects.filter(pedido=OuterRef("pk"))
        .values("pedido").annotate(s=Sum("monto")).values("s")
    )
    return qs.annotate(
        pagado_sum=Coalesce(Subquery(pagos, output_field=DecimalField()), Value(Decimal("0")),
                            output_field=DecimalField()),
    ).annotate(saldo_pend=ExpressionWrapper(F("total") - F("pagado_sum"), output_field=DecimalField()))


@login_required
def pedido_list(request):
    estado = request.GET.get("estado", "pendientes")
    q = request.GET.get("q", "").strip()

    pedidos = _con_pagado(PedidoVario.objects.prefetch_related("productos"))
    if q:
        filtro = Q(cliente__icontains=q) | Q(telefono__icontains=q) | Q(productos__producto__icontains=q)
        folio = q.upper().removeprefix("V-").lstrip("0")
        if folio.isdigit():
            filtro |= Q(pk=int(folio))
        pedidos = pedidos.filter(filtro).distinct()

    conteos = dict(PedidoVario.objects.values_list("estado").annotate(n=Count("id")))
    if estado == "pendientes":
        pedidos = pedidos.filter(estado__in=PedidoVario.PENDIENTES)
    elif estado in dict(PedidoVario.ESTADOS):
        pedidos = pedidos.filter(estado=estado)
    else:
        estado = "todos"
    if estado in ("entregado", "todos"):
        pedidos = pedidos.order_by("-fecha_entrega", "-id")

    filtros = [("pendientes", "Pendientes", sum(conteos.get(e, 0) for e in PedidoVario.PENDIENTES))]
    filtros += [(k, v, conteos.get(k, 0)) for k, v in PedidoVario.ESTADOS]
    filtros += [("todos", "Todos", sum(conteos.values()))]

    return render(request, "varios/pedido_list.html", {
        "pedidos": pedidos,
        "filtros": filtros,
        "estado_actual": estado,
        "busqueda": q,
        "hoy": timezone.localdate(),
    })


def _guardar_pedido(request, pedido=None):
    nuevo = pedido is None
    pedido = pedido or PedidoVario()
    form = PedidoVarioForm(request.POST or None, instance=pedido)
    formset = ProductoFormSet(request.POST or None, instance=pedido, prefix="productos")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            pedido = form.save()
            formset.instance = pedido
            formset.save()
            pedido.calcular_total()
            anticipo = form.cleaned_data.get("anticipo") if nuevo else None
            if anticipo:
                PagoPedidoVario.objects.create(
                    pedido=pedido, monto=anticipo,
                    forma_pago=form.cleaned_data.get("forma_anticipo") or "efectivo",
                )
        messages.success(request, f"Pedido {pedido.folio} {'creado' if nuevo else 'actualizado'}.")
        return redirect("varios:pedido_detail", pk=pedido.pk)

    return render(request, "varios/pedido_form.html", {
        "form": form,
        "formset": formset,
        "pedido": None if nuevo else pedido,
    })


@login_required
def pedido_create(request):
    return _guardar_pedido(request)


@login_required
def pedido_update(request, pk):
    return _guardar_pedido(request, get_object_or_404(PedidoVario, pk=pk))


@login_required
def pedido_detail(request, pk):
    pedido = get_object_or_404(PedidoVario, pk=pk)
    pagos = pedido.pagos.all()
    pagado = sum((p.monto for p in pagos), Decimal("0"))
    return render(request, "varios/pedido_detail.html", {
        "pedido": pedido,
        "productos": pedido.productos.all(),
        "pagos": pagos,
        "pagado": pagado,
        "saldo": max(pedido.total - pagado, Decimal("0")),
        "estados": PedidoVario.ESTADOS,
    })


@login_required
@require_POST
def pedido_estado(request, pk):
    pedido = get_object_or_404(PedidoVario, pk=pk)
    estado = request.POST.get("estado")
    if estado in dict(PedidoVario.ESTADOS):
        pedido.estado = estado
        pedido.save(update_fields=["estado", "actualizado"])
        messages.success(request, f"{pedido.folio}: {pedido.get_estado_display()}.")
    return redirect("varios:pedido_detail", pk=pedido.pk)


@login_required
def pedido_delete(request, pk):
    pedido = get_object_or_404(PedidoVario, pk=pk)
    if request.method == "POST":
        folio = pedido.folio
        pedido.delete()
        messages.success(request, f"Se eliminó el pedido {folio}.")
        return redirect("varios:pedido_list")
    return render(request, "varios/confirm_delete.html", {
        "titulo": f"Eliminar pedido {pedido.folio}",
        "mensaje": f"Se borrará el pedido de {pedido.cliente} con sus productos y pagos. No se puede deshacer.",
        "volver": pedido,
    })


@login_required
def pago_create(request, pk):
    pedido = get_object_or_404(PedidoVario, pk=pk)
    form = PagoForm(request.POST or None, initial={"monto": pedido.saldo or None})
    if request.method == "POST" and form.is_valid():
        pago = form.save(commit=False)
        pago.pedido = pedido
        pago.save()
        messages.success(request, f"Pago de ${pago.monto} registrado en {pedido.folio}.")
        return redirect("varios:pedido_detail", pk=pedido.pk)
    return render(request, "varios/pago_form.html", {"form": form, "pedido": pedido})


@login_required
def pago_delete(request, pk):
    pago = get_object_or_404(PagoPedidoVario.objects.select_related("pedido"), pk=pk)
    pedido = pago.pedido
    if request.method == "POST":
        pago.delete()
        messages.success(request, f"Se eliminó el pago de ${pago.monto}.")
        return redirect("varios:pedido_detail", pk=pedido.pk)
    return render(request, "varios/confirm_delete.html", {
        "titulo": "Eliminar pago",
        "mensaje": f"Se borrará el pago de ${pago.monto} del {pago.fecha:%d/%m/%Y} del pedido {pedido.folio}.",
        "volver": pedido,
    })
