from django.views.generic import DetailView, CreateView, UpdateView
from django.db.models import Count
from apps.escuelas.models import Grupo
from django.urls import reverse
from .models import Alumno
from .forms import AlumnoForm


class GrupoDetailView(DetailView):
    model = Grupo
    template_name = "alumnos/grupo_detail.html"
    context_object_name = "grupo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        alumnos = Alumno.objects.filter(
            grupo=self.object
        ).order_by("nombre")

        context["alumnos"] = alumnos
        context["total_alumnos"] = alumnos.count()

        return context
    


class AlumnoCreateView(CreateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = "alumnos/alumno_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["grupo_id"] = self.kwargs["grupo_id"]
        return kwargs

    def form_valid(self, form):
        form.instance.grupo_id = self.kwargs["grupo_id"]
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("grupo_detail", kwargs={"pk": self.kwargs["grupo_id"]})
    

class AlumnoUpdateView(UpdateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = "alumnos/alumno_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["grupo_id"] = self.object.grupo_id  # 👈 CLAVE
        return kwargs

    def get_success_url(self):
        return reverse(
            "grupo_detail",
            kwargs={"pk": self.object.grupo.id}
        )