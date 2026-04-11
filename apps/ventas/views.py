from django.views.generic import CreateView, DetailView
from django.urls import reverse
from .models import Pedido

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