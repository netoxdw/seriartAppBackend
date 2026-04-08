from django.views.generic import DetailView
from django.views.generic import FormView
from django.urls import reverse
from django import forms
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


class EscuelaForm(forms.Form):
    escuela_existente = forms.ModelChoiceField(
        queryset=Escuela.objects.all(),
        required=False,
        label="Escuela existente"
    )

    nombre = forms.CharField(required=False)
    direccion = forms.CharField(required=False)
    telefono = forms.CharField(required=False)

class EscuelaCreateView(FormView):
    template_name = "escuelas/escuela_form.html"
    form_class = EscuelaForm

    def dispatch(self, request, *args, **kwargs):
        self.generacion = Generacion.objects.get(pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        escuela = form.cleaned_data.get("escuela_existente")

        if escuela:
            # usar existente
            self.generacion.escuelas.add(escuela)

        else:
            # crear nueva
            escuela = Escuela.objects.create(
                nombre=form.cleaned_data["nombre"],
                direccion=form.cleaned_data["direccion"],
                telefono=form.cleaned_data["telefono"]
            )
            escuela.generaciones.add(self.generacion)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("generacion_detail", kwargs={"pk": self.generacion.id})