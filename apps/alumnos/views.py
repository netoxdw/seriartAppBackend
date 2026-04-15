from django.views.generic import DetailView, CreateView, UpdateView
from django.db.models import Count
from apps.escuelas.models import Grupo
from apps.ventas.models import Pedido
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
    

from django.shortcuts import redirect


class AlumnoCreateView(CreateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = "alumnos/alumno_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["grupo_id"] = self.kwargs["grupo_id"]
        return kwargs

    def form_valid(self, form):
        # 🔥 asignar grupo
        form.instance.grupo_id = self.kwargs["grupo_id"]

        # 🔥 guardar alumno SIN usar super()
        self.object = form.save()

        # 🔥 crear pedido
        pedido, created = Pedido.objects.get_or_create(alumno=self.object)

        # 🔥 redirigir manualmente
        return redirect("pedido_detail", pk=pedido.id)
    

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
    


class AlumnoDetailView(DetailView):
    model = Alumno
    template_name = "alumnos/alumno_detail.html"
    context_object_name = "alumno"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedidos = self.object.pedidos.all()

        context["pedidos"] = pedidos
        context["total_pedidos"] = pedidos.count()

        return context