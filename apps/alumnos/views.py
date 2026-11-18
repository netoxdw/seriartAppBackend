from django.views.generic import DetailView, CreateView, UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from decimal import Decimal

from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import Coalesce

from django.contrib.auth.mixins import LoginRequiredMixin

from apps.escuelas.models import Grupo
from apps.ventas.models import Pedido

from .models import Alumno
from .forms import AlumnoForm


class GrupoDetailView(LoginRequiredMixin, DetailView):

    model = Grupo

    template_name = "alumnos/grupo_detail.html"

    context_object_name = "grupo"

    def get_queryset(self):
        return Grupo.objects.select_related("escuela", "generacion")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pedidos = Pedido.objects.annotate(
            pagado=Coalesce(Sum("pagos__monto"), Decimal("0"))
        ).order_by("id")
        alumnos = list(
            Alumno.objects.filter(grupo=self.object)
            .order_by("nombre_alumno")
            .prefetch_related(Prefetch("pedidos", queryset=pedidos))
        )

        conteo = {}
        for alumno in alumnos:
            ps = list(alumno.pedidos.all())
            alumno.pedido = ps[0] if ps else None
            p = alumno.pedido
            if p:
                p.saldo = max(p.total - p.pagado, Decimal("0"))
            clave = p.estado if p else "sin_pedido"
            alumno.clave_estado = clave
            conteo[clave] = conteo.get(clave, 0) + 1

        # Todos los estados siempre visibles (en orden del proceso), aunque estén en cero
        estados = [
            {"clave": clave, "nombre": nombre, "color": Pedido.COLORES_ESTADO.get(clave, "secondary"),
             "n": conteo.get(clave, 0)}
            for clave, nombre in Pedido.ESTADO_CHOICES
        ]
        if conteo.get("sin_pedido"):
            estados.insert(0, {"clave": "sin_pedido", "nombre": "Sin pedido", "color": "light",
                               "n": conteo["sin_pedido"]})

        context["alumnos"] = alumnos
        context["total_alumnos"] = len(alumnos)
        context["estados"] = estados

        return context


def _siguiente(request):
    """URL a la que volver (?next=), solo si es de este sitio."""
    url = request.POST.get("next") or request.GET.get("next") or ""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return ""


class AlumnoCreateView(LoginRequiredMixin, CreateView):

    model = Alumno

    form_class = AlumnoForm

    template_name = "alumnos/alumno_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.grupo = get_object_or_404(
            Grupo.objects.select_related("escuela", "generacion"), pk=kwargs["grupo_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["grupo_id"] = self.grupo.id

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["grupo"] = self.grupo
        context["cancelar"] = reverse("alumnos:grupo_detail", kwargs={"pk": self.grupo.id})
        return context

    def form_valid(self, form):

        # asignar grupo
        form.instance.grupo = self.grupo

        # guardar alumno
        self.object = form.save()

        # crear pedido automáticamente
        pedido, created = Pedido.objects.get_or_create(
            alumno=self.object
        )

        # directo a la captura rápida de artículos
        return redirect(
            "ventas:pedido_captura",
            pk=pedido.id
        )


class AlumnoUpdateView(LoginRequiredMixin, UpdateView):

    model = Alumno

    form_class = AlumnoForm

    template_name = "alumnos/alumno_form.html"

    def get_queryset(self):
        return Alumno.objects.select_related("grupo__escuela", "grupo__generacion")

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["grupo_id"] = self.object.grupo_id

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["grupo"] = self.object.grupo
        context["siguiente"] = _siguiente(self.request)
        context["cancelar"] = context["siguiente"] or reverse(
            "alumnos:grupo_detail", kwargs={"pk": self.object.grupo_id}
        )
        return context

    def get_success_url(self):
        # Si vino desde el pedido (?next=), regresa ahí; si no, al grupo
        return _siguiente(self.request) or reverse(
            "alumnos:grupo_detail",
            kwargs={
                "pk": self.object.grupo_id
            }
        )


class AlumnoDetailView(LoginRequiredMixin, DetailView):

    model = Alumno

    template_name = "alumnos/alumno_detail.html"

    context_object_name = "alumno"

    def get_queryset(self):
        return Alumno.objects.select_related("grupo__escuela", "grupo__generacion")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pedidos = list(
            self.object.pedidos.annotate(
                pagado=Coalesce(Sum("pagos__monto"), Decimal("0"))
            ).order_by("-fecha", "-id")
        )
        for p in pedidos:
            p.saldo = max(p.total - p.pagado, Decimal("0"))

        context["pedidos"] = pedidos

        context["total_pedidos"] = len(pedidos)

        return context
