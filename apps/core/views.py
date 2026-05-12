from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.db.models import Count

from django.contrib.auth.mixins import LoginRequiredMixin

from apps.escuelas.models import Generacion


class HomeView(LoginRequiredMixin, TemplateView):

    template_name = "home.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        generaciones = Generacion.objects.annotate(
            num_escuelas=Count("escuelas")
        )

        context["generaciones"] = generaciones

        return context


class GeneracionCreateView(LoginRequiredMixin, CreateView):

    model = Generacion

    fields = ["nombre", "anio"]

    template_name = "generaciones/create.html"

    success_url = reverse_lazy("home")