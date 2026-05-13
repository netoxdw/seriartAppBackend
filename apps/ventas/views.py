from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView, View
from django.urls import reverse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from apps.alumnos.models import Alumno
from .models import PedidoItemBase, Pedido, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento
from .form import PedidoItemBaseForm, PedidoItemAnilloForm, PedidoItemExtraForm, ObservacionForm, PagoForm, PedidoDescuentoForm, PedidoCambiarEstadoForm
from apps.catalogo.models import PrecioBaseGeneracion



class PedidoCreateView(LoginRequiredMixin, CreateView):
    model = Pedido
    fields = []
    template_name = "ventas/pedido_form.html"

    def form_valid(self, form):
        form.instance.alumno_id = self.kwargs["alumno_id"]
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.id}
        )
    

class PedidoDetailView(LoginRequiredMixin, DetailView):

    model = Pedido

    template_name = "ventas/pedido_detail.html"

    context_object_name = "pedido"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pedido = self.object

        # ========================================
        # ITEMS
        # ========================================

        items_base = pedido.items_base.all()

        items_anillo = pedido.items_anillo.all()

        items_extra = pedido.items_extra.all()

        context["items_base"] = items_base
        context["items_anillo"] = items_anillo
        context["items_extra"] = items_extra

        # ========================================
        # DESCUENTOS
        # ========================================

        descuentos = pedido.descuentos.all()

        total_descuentos = sum(
            d.monto for d in descuentos
        )

        context["descuentos"] = descuentos

        context["total_descuentos"] = total_descuentos

        # ========================================
        # TOTALES
        # ========================================

        total = pedido.total

        total_pagado = pedido.total_pagado

        saldo_pendiente = total - total_pagado

        subtotal = total + total_descuentos

        context["subtotal"] = subtotal

        context["total"] = total

        context["total_pagado"] = total_pagado

        context["saldo_pendiente"] = saldo_pendiente

        # ========================================
        # PORCENTAJE PAGADO
        # ========================================

        if total > 0:

            porcentaje_pagado = (
                total_pagado / total
            ) * 100

        else:

            porcentaje_pagado = 0

        context["porcentaje_pagado"] = round(
            porcentaje_pagado,
            2
        )

        return context


class PedidoEntregaListView(ListView):

    model = Pedido
    template_name = "ventas/pedido_entrega_list.html"
    context_object_name = "pedidos"
    paginate_by = 20

    def get_queryset(self):

        queryset = (
            Pedido.objects
            .select_related("alumno")
            .order_by("-id")
        )

        # =========================
        # FILTRO POR ESTADO
        # =========================

        estado = self.request.GET.get("estado")

        if estado:
            queryset = queryset.filter(estado=estado)

        # =========================
        # BUSCADOR
        # =========================

        q = self.request.GET.get("q")

        if q:
            queryset = queryset.filter(
                Q(id__icontains=q) |
                Q(alumno__nombre__icontains=q) |
                Q(alumno__telefono__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["estado_actual"] = self.request.GET.get("estado", "")
        context["busqueda"] = self.request.GET.get("q", "")

        context["estados"] = [
            ("pendiente", "Pendiente"),
            ("proceso", "En proceso"),
            ("listo", "Listo"),
            ("entregado", "Entregado"),
        ]

        return context

# ############## itembase



# ==============================
# 🧾 CREAR ITEM BASE
# ==============================

class PedidoItemBaseCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        context["pedido"] = pedido
        context["pedido_id"] = pedido.id

        # 🔥 OBTENER TAMAÑOS DISPONIBLES
        generacion = pedido.alumno.grupo.generacion

        precios = PrecioBaseGeneracion.objects.filter(
            generacion=generacion
        ).select_related("modelo__tamano_producto")

        tamanos_dict = {}

        for p in precios:
            t = p.modelo.tamano_producto
            tamanos_dict[t.id] = t.nombre

        context["tamanos"] = [
            {"id": k, "nombre": v}
            for k, v in tamanos_dict.items()
        ]

        return context

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.kwargs["pedido_id"]}
        )


# ==============================
# ⚡ AJAX → CARGAR SECCIONES
# ==============================
@login_required
def cargar_secciones(request):
    tamano_id = request.GET.get("tamano")
    generacion_id = request.GET.get("generacion")

    if not tamano_id or not generacion_id:
        return JsonResponse([], safe=False)

    precios = PrecioBaseGeneracion.objects.filter(
        generacion_id=generacion_id,
        modelo__tamano_producto_id=tamano_id
    ).select_related("modelo__seccion")

    # 🔥 evitar duplicados
    secciones_dict = {}

    for p in precios:
        s = p.modelo.seccion
        secciones_dict[s.id] = s.nombre

    data = [
        {"id": k, "nombre": v}
        for k, v in secciones_dict.items()
    ]

    return JsonResponse(data, safe=False)


# ==============================
# ⚡ AJAX → CARGAR MODELOS
# ==============================
@login_required
def cargar_modelos(request):
    tamano_id = request.GET.get("tamano")
    seccion_id = request.GET.get("seccion")
    generacion_id = request.GET.get("generacion")

    if not tamano_id or not seccion_id or not generacion_id:
        return JsonResponse([], safe=False)

    precios = PrecioBaseGeneracion.objects.filter(
        generacion_id=generacion_id,
        modelo__tamano_producto_id=tamano_id,
        modelo__seccion_id=seccion_id
    ).select_related("modelo")

    data = [
        {
            "id": p.modelo.id,
            "nombre": p.modelo.nombre
        }
        for p in precios
    ]

    return JsonResponse(data, safe=False)

# 🔁 REDIRECT ALUMNO → PEDIDO
@login_required
def alumno_pedido_redirect(request, alumno_id):
    alumno = get_object_or_404(
    Alumno,
    id=alumno_id
)

    pedido = Pedido.objects.filter(alumno=alumno).first()

    if not pedido:
        pedido = Pedido.objects.create(alumno=alumno)

    return redirect("pedido_detail", pk=pedido.id)


# ✏️ UPDATE

class PedidoItemBaseUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id  # 🔥 clave
        return context

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido_id}
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.object.pedido
        return kwargs

class PedidoItemBaseDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemBase
    template_name = "ventas/itembase_confirm_delete.html"


    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido.id}
        )
    
# Anillos ########################################################################333

class PedidoItemAnilloCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemAnillo
    form_class = PedidoItemAnilloForm
    template_name = "ventas/itemanillo_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]  # 🔥 clave
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = Pedido.objects.get(id=self.kwargs["pedido_id"])
        return kwargs

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})
    
class PedidoItemAnilloUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemAnillo
    form_class = PedidoItemAnilloForm
    template_name = "ventas/itemanillo_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id  # 🔥 clave
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.object.pedido
        return kwargs


class PedidoItemAnilloDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemAnillo
    template_name = "ventas/itemanillo_confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido_id}
        )
    
# EXTRAS #################################################################

# ➕ CREATE
class PedidoItemExtraCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemExtra
    form_class = PedidoItemExtraForm
    template_name = "ventas/itemextra_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


# ✏️ UPDATE
class PedidoItemExtraUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemExtra
    form_class = PedidoItemExtraForm
    template_name = "ventas/itemextra_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


# 🗑 DELETE
class PedidoItemExtraDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemExtra
    template_name = "ventas/itemextra_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# Observacion ######################################################################

# ➕ CREATE
class ObservacionCreateView(LoginRequiredMixin, CreateView):
    model = Observacion
    form_class = ObservacionForm
    template_name = "ventas/observacion_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


# ✏️ UPDATE
class ObservacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Observacion
    form_class = ObservacionForm
    template_name = "ventas/observacion_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


# 🗑 DELETE
class ObservacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Observacion
    template_name = "ventas/observacion_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


# Pago #####################################################################################

class PagoCreateView(LoginRequiredMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = "ventas/pago_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


class PagoDeleteView(LoginRequiredMixin, DeleteView):
    model = Pago
    template_name = "ventas/pago_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# DESCUENTO ###############################################################################3


# ✅ CREAR
class PedidoDescuentoCreateView(LoginRequiredMixin, CreateView):
    model = PedidoDescuento
    form_class = PedidoDescuentoForm
    template_name = "ventas/descuento_form.html"

    def form_valid(self, form):
        form.instance.pedido = get_object_or_404(
            Pedido, id=self.kwargs["pedido_id"]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context


# ✏️ EDITAR
class PedidoDescuentoUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoDescuento
    form_class = PedidoDescuentoForm
    template_name = "ventas/descuento_form.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context


# 🗑️ ELIMINAR
class PedidoDescuentoDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoDescuento
    template_name = "ventas/descuento_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


# Cambiar estado de panel de entregas

class PedidoCambiarEstadoView(View):

    template_name = "ventas/pedido_cambiar_estado.html"

    def get(self, request, pk):

        pedido = get_object_or_404(
            Pedido,
            pk=pk
        )

        form = PedidoCambiarEstadoForm(
            instance=pedido
        )

        context = {
            "pedido": pedido,
            "form": form,
        }

        return render(
            request,
            self.template_name,
            context
        )

    def post(self, request, pk):

        pedido = get_object_or_404(
            Pedido,
            pk=pk
        )

        form = PedidoCambiarEstadoForm(
            request.POST,
            instance=pedido
        )

        if form.is_valid():

            pedido = form.save(commit=False)

            # =========================
            # FECHA ENTREGA
            # =========================

            if pedido.estado == "entregado":

                if not pedido.fecha_entrega:
                    pedido.fecha_entrega = timezone.now()

            else:

                pedido.fecha_entrega = None
                pedido.recibido_por = None

            pedido.save()

            messages.success(
                request,
                "Estado actualizado correctamente."
            )

            return redirect(
                "ventas:pedido_entrega_list"
            )

        context = {
            "pedido": pedido,
            "form": form,
        }

        return render(
            request,
            self.template_name,
            context
        )