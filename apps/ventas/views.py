from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse
from django.shortcuts import redirect
from .models import PedidoItemBase, Pedido
from apps.alumnos.models import Alumno
from .forms import PedidoItemBaseForm


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


class PedidoItemBaseCreateView(CreateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.kwargs["pedido_id"]}
        )

def alumno_pedido_redirect(request, alumno_id):
    alumno = Alumno.objects.get(id=alumno_id)

    # Buscar pedido existente
    pedido = Pedido.objects.filter(alumno=alumno).first()

    # Si no existe, crearlo
    if not pedido:
        pedido = Pedido.objects.create(alumno=alumno)

    return redirect("pedido_detail", pk=pedido.id)



class PedidoItemBaseUpdateView(UpdateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    # def get_success_url(self):
    #     pedido_id = self.object.pedido_id  # 👈 clave
    #     return reverse("pedido_detail", kwargs={"pk": pedido_id})
    def get_success_url(self):
        return reverse("pedido_detail", kwargs={"pk": self.object.pedido_id})


class PedidoItemBaseDeleteView(DeleteView):
    model = PedidoItemBase
    template_name = "ventas/itembase_confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "pedido_detail",
            kwargs={"pk": self.object.pedido.id}
        )