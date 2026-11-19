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
            num_escuelas=Count("escuelas", distinct=True),
            num_grupos=Count("grupos", distinct=True),
            num_alumnos=Count("grupos__alumnos", distinct=True),
            num_pedidos=Count("grupos__alumnos__pedidos", distinct=True),
        ).order_by("-anio")  # con annotate Django ignora Meta.ordering

        context["generaciones"] = generaciones

        return context


class GeneracionCreateView(LoginRequiredMixin, CreateView):

    model = Generacion

    fields = ["nombre_generacion", "anio"]

    template_name = "generaciones/create.html"

    success_url = reverse_lazy("home")

# ==============================
# 🔎 BUSCADOR GLOBAL: escuelas, grupos y alumnos
# ==============================

from functools import reduce
import operator

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.shortcuts import render

from apps.alumnos.models import Alumno
from apps.escuelas.models import Escuela, Grupo
from apps.ventas.models import Pedido

LIMITE_RESULTADOS = 50


def _filtro_palabras(palabras, campos):
    """Cada palabra debe aparecer en alguno de los campos (AND entre palabras, OR entre campos)."""
    return reduce(
        operator.and_,
        (reduce(operator.or_, (Q(**{f"{c}__icontains": p}) for c in campos)) for p in palabras),
    )


@login_required
def buscar(request):
    q = " ".join(request.GET.get("q", "").split())[:100]
    palabras = q.split()
    contexto = {"q": q, "escuelas": [], "grupos": [], "alumnos": [], "totales": {}}

    if palabras:
        escuelas = (
            Escuela.objects.filter(_filtro_palabras(palabras, ["nombre_escuela", "direccion", "telefono"]))
            .prefetch_related("generaciones")
            .annotate(num_grupos=Count("grupos", distinct=True))
            .order_by("nombre_escuela")
        )
        grupos = (
            Grupo.objects.filter(_filtro_palabras(palabras, ["nombre_grupo", "escuela__nombre_escuela"]))
            .select_related("escuela", "generacion")
            .annotate(num_alumnos=Count("alumnos", distinct=True))
            .order_by("-generacion__anio", "escuela__nombre_escuela", "nombre_grupo")
        )
        alumnos = (
            Alumno.objects.filter(_filtro_palabras(palabras, [
                "nombre_alumno", "telefono", "folio_fotos",
                "grupo__nombre_grupo", "grupo__escuela__nombre_escuela",
            ]))
            .select_related("grupo__escuela", "grupo__generacion")
            .prefetch_related(Prefetch("pedidos", queryset=Pedido.objects.order_by("id")))
            .order_by("nombre_alumno")
        )
        contexto["totales"] = {
            "escuelas": escuelas.count(),
            "grupos": grupos.count(),
            "alumnos": alumnos.count(),
        }
        contexto["escuelas"] = escuelas[:LIMITE_RESULTADOS]
        contexto["grupos"] = grupos[:LIMITE_RESULTADOS]
        contexto["alumnos"] = [
            {"alumno": a, "pedido": next(iter(a.pedidos.all()), None)}
            for a in alumnos[:LIMITE_RESULTADOS]
        ]

    contexto["limite"] = LIMITE_RESULTADOS
    contexto["sin_resultados"] = bool(palabras) and not any(contexto["totales"].values())
    return render(request, "buscar.html", contexto)
