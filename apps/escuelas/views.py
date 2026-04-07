from django.views.generic import DetailView
from .models import Generacion, Escuela


class GeneracionDetailView(DetailView):
    model = Generacion
    template_name = "escuelas/generacion_detail.html"
    context_object_name = "generacion"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        escuelas = Escuela.objects.filter(
            generaciones=self.object
        )

        context["escuelas"] = escuelas
        return context