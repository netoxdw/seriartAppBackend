from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.http import JsonResponse


from apps.alumnos.models import Alumno
from .models import PedidoItemBase, Pedido, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento
from .form import PedidoItemBaseForm, PedidoItemAnilloForm, PedidoItemExtraForm, ObservacionForm, PagoForm, PedidoDescuentoForm
from django.http import JsonResponse
from apps.catalogo.models import PrecioBaseGeneracion



class PedidoCreateView(CreateView):
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
    

class PedidoDetailView(DetailView):
    model = Pedido
    template_name = "ventas/pedido_detail.html"
    context_object_name = "pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedido = self.object

        # 🧾 ITEMS
        context["items_base"] = pedido.items_base.all()
        context["items_anillo"] = pedido.items_anillo.all()
        context["items_extra"] = pedido.items_extra.all()

        # 💸 DESCUENTOS
        descuentos = pedido.descuentos.all()
        total_descuentos = sum(d.monto for d in descuentos)

        context["descuentos"] = descuentos
        context["total_descuentos"] = total_descuentos

        # 🔥 CLAVE (AQUÍ ESTABA EL PROBLEMA)
        context["subtotal"] = pedido.total + total_descuentos

        return context


# ############## itembase



# ==============================
# 🧾 CREAR ITEM BASE
# ==============================

class PedidoItemBaseCreateView(CreateView):
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

def alumno_pedido_redirect(request, alumno_id):
    alumno = Alumno.objects.get(id=alumno_id)

    pedido = Pedido.objects.filter(alumno=alumno).first()

    if not pedido:
        pedido = Pedido.objects.create(alumno=alumno)

    return redirect("pedido_detail", pk=pedido.id)


# ✏️ UPDATE

class PedidoItemBaseUpdateView(UpdateView):
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

class PedidoItemBaseDeleteView(DeleteView):
    model = PedidoItemBase
    template_name = "ventas/itembase_confirm_delete.html"


    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido.id}
        )
    
# Anillos ########################################################################333

class PedidoItemAnilloCreateView(CreateView):
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
    
class PedidoItemAnilloUpdateView(UpdateView):
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


class PedidoItemAnilloDeleteView(DeleteView):
    model = PedidoItemAnillo
    template_name = "ventas/itemanillo_confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido_id}
        )
    
# EXTRAS #################################################################

# ➕ CREATE
class PedidoItemExtraCreateView(CreateView):
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
class PedidoItemExtraUpdateView(UpdateView):
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
class PedidoItemExtraDeleteView(DeleteView):
    model = PedidoItemExtra
    template_name = "ventas/itemextra_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# Observacion ######################################################################

# ➕ CREATE
class ObservacionCreateView(CreateView):
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
class ObservacionUpdateView(UpdateView):
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
class ObservacionDeleteView(DeleteView):
    model = Observacion
    template_name = "ventas/observacion_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


# Pago #####################################################################################

class PagoCreateView(CreateView):
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


class PagoDeleteView(DeleteView):
    model = Pago
    template_name = "ventas/pago_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# DESCUENTO ###############################################################################3


# ✅ CREAR
class PedidoDescuentoCreateView(CreateView):
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
class PedidoDescuentoUpdateView(UpdateView):
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
class PedidoDescuentoDeleteView(DeleteView):
    model = PedidoDescuento
    template_name = "ventas/descuento_confirm_delete.html"

    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})
