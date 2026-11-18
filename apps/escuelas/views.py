from django.views.generic import (
    DetailView,
    FormView,
    CreateView,
    UpdateView
)

from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Generacion, Escuela, Grupo
from .forms import GrupoForm, EscuelaForm, EscuelaUpdateForm


class GeneracionDetailView(LoginRequiredMixin, DetailView):

    model = Generacion

    template_name = "escuelas/generacion_detail.html"

    context_object_name = "generacion"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        gen = self.object
        de_esta_gen = Q(grupos__generacion=gen)
        escuelas = (
            Escuela.objects.filter(generaciones=gen)
            .annotate(
                num_grupos=Count("grupos", filter=de_esta_gen, distinct=True),
                num_alumnos=Count("grupos__alumnos", filter=de_esta_gen, distinct=True),
            )
            .order_by("nombre_escuela")
        )

        context["escuelas"] = escuelas
        context["totales"] = {
            "grupos": sum(e.num_grupos for e in escuelas),
            "alumnos": sum(e.num_alumnos for e in escuelas),
            "sin_nivel": sum(1 for e in escuelas if e.nivel == Escuela.NIVEL_OTRO),
        }

        return context


class EscuelaCreateView(LoginRequiredMixin, FormView):

    template_name = "escuelas/escuela_form.html"

    form_class = EscuelaForm

    def dispatch(self, request, *args, **kwargs):

        self.generacion = get_object_or_404(Generacion, pk=kwargs["pk"])

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["generacion"] = self.generacion
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["generacion"] = self.generacion
        return context

    def form_valid(self, form):

        escuela = form.cleaned_data.get(
            "escuela_existente"
        )

        if escuela:

            # usar existente
            self.generacion.escuelas.add(
                escuela
            )

        else:

            # crear nueva
            escuela = Escuela.objects.create(
                nombre_escuela=form.cleaned_data["nombre_escuela"],
                nivel=form.cleaned_data.get("nivel") or Escuela.NIVEL_OTRO,
                direccion=form.cleaned_data["direccion"],
                telefono=form.cleaned_data["telefono"]
            )

            escuela.generaciones.add(
                self.generacion
            )

        return super().form_valid(form)

    def get_success_url(self):

        return reverse(
            "escuelas:generacion_detail",
            kwargs={
                "pk": self.generacion.id
            }
        )


class EscuelaDetailView(LoginRequiredMixin, DetailView):

    model = Escuela

    template_name = "escuelas/escuela_detail.html"

    context_object_name = "escuela"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        generacion = get_object_or_404(Generacion, pk=self.kwargs["generacion_id"])

        grupos = Grupo.objects.filter(
            escuela=self.object,
            generacion=generacion
        ).annotate(
            num_alumnos=Count(
                "alumnos",
                distinct=True
            )
        ).order_by("nombre_grupo")

        context["generacion"] = generacion

        context["grupos"] = grupos
        context["total_alumnos"] = sum(g.num_alumnos for g in grupos)
        context["sin_fecha"] = sum(1 for g in grupos if not g.fecha_fotografia)

        return context


class GrupoCreateView(LoginRequiredMixin, CreateView):

    model = Grupo

    form_class = GrupoForm

    template_name = "escuelas/grupo_form.html"

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["escuela"] = self.kwargs["escuela_id"]

        kwargs["generacion"] = self.kwargs["generacion_id"]

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["escuela"] = get_object_or_404(Escuela, pk=self.kwargs["escuela_id"])
        context["generacion"] = get_object_or_404(Generacion, pk=self.kwargs["generacion_id"])
        return context

    def form_valid(self, form):

        form.instance.escuela_id = self.kwargs["escuela_id"]

        form.instance.generacion_id = self.kwargs["generacion_id"]

        return super().form_valid(form)

    def get_success_url(self):

        return reverse(
            "escuelas:escuela_detail",
            kwargs={
                "generacion_id": self.kwargs["generacion_id"],
                "pk": self.kwargs["escuela_id"]
            }
        )


class GrupoUpdateView(LoginRequiredMixin, UpdateView):

    model = Grupo

    form_class = GrupoForm

    template_name = "escuelas/grupo_form.html"

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["escuela"] = self.object.escuela_id

        kwargs["generacion"] = self.object.generacion_id

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["escuela"] = self.object.escuela
        context["generacion"] = self.object.generacion
        return context

    def get_success_url(self):

        return reverse(
            "escuelas:escuela_detail",
            kwargs={
                "generacion_id": self.object.generacion.id,
                "pk": self.object.escuela.id
            }
        )


class EscuelaUpdateView(LoginRequiredMixin, UpdateView):

    model = Escuela

    form_class = EscuelaUpdateForm

    template_name = "escuelas/escuela_update.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["generacion"] = get_object_or_404(Generacion, pk=self.kwargs["generacion_id"])
        return context

    def get_success_url(self):
        return reverse(
            "escuelas:escuela_detail",
            kwargs={"generacion_id": self.kwargs["generacion_id"], "pk": self.object.pk},
        )
