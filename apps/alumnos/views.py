from django.views.generic import DetailView, CreateView, UpdateView
from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Count

from django.contrib.auth.mixins import LoginRequiredMixin

from apps.escuelas.models import Grupo
from apps.ventas.models import Pedido

from .models import Alumno
from .forms import AlumnoForm


class GrupoDetailView(LoginRequiredMixin, DetailView):

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


class AlumnoCreateView(LoginRequiredMixin, CreateView):

    model = Alumno

    form_class = AlumnoForm

    template_name = "alumnos/alumno_form.html"

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["grupo_id"] = self.kwargs["grupo_id"]

        return kwargs

    def form_valid(self, form):

        # asignar grupo
        form.instance.grupo_id = self.kwargs["grupo_id"]

        # guardar alumno
        self.object = form.save()

        # crear pedido automáticamente
        pedido, created = Pedido.objects.get_or_create(
            alumno=self.object
        )

        return redirect(
            "ventas:pedido_detail",
            pk=pedido.id
        )


class AlumnoUpdateView(LoginRequiredMixin, UpdateView):

    model = Alumno

    form_class = AlumnoForm

    template_name = "alumnos/alumno_form.html"

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["grupo_id"] = self.object.grupo_id

        return kwargs

    def get_success_url(self):

        return reverse(
            "alumnos:grupo_detail",
            kwargs={
                "pk": self.object.grupo.id
            }
        )


class AlumnoDetailView(LoginRequiredMixin, DetailView):

    model = Alumno

    template_name = "alumnos/alumno_detail.html"

    context_object_name = "alumno"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pedidos = self.object.pedidos.all()

        context["pedidos"] = pedidos

        context["total_pedidos"] = pedidos.count()

        return context