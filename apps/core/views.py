from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from apps.escuelas.models import Generacion


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["generaciones"] = Generacion.objects.all()
        return context


class GeneracionCreateView(CreateView):
    model = Generacion
    fields = ["nombre", "anio"]
    template_name = "generaciones/create.html"
    success_url = reverse_lazy("home")