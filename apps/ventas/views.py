from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse
from django.shortcuts import redirect
from apps.alumnos.models import Alumno
from .models import PedidoItemBase, Pedido, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago
from .form import PedidoItemBaseForm, PedidoItemAnilloForm, PedidoItemExtraForm, ObservacionForm, PagoForm


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

        context["items_base"] = self.object.items_base.all()
        context["items_anillo"] = self.object.items_anillo.all()
        context["items_extra"] = self.object.items_extra.all()

        return context



# ############## itembase

class PedidoItemBaseCreateView(CreateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]  # 🔥 clave
        return context

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.kwargs["pedido_id"]}
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = Pedido.objects.get(id=self.kwargs["pedido_id"])
        return kwargs
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = Pedido.objects.get(id=self.kwargs["pedido_id"])
        return kwargs


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
