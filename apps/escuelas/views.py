from django.views.generic import DetailView, FormView, CreateView
from django.urls import reverse
from django import forms
from .models import Generacion, Escuela, Grupo
from django.db.models import Count




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


class EscuelaDetailView(DetailView):
    model = Escuela
    template_name = "escuelas/escuela_detail.html"
    context_object_name = "escuela"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        generacion = Generacion.objects.get(id=self.kwargs["generacion_id"])

        grupos = Grupo.objects.filter(
            escuela=self.object,
            generacion=generacion
        ).annotate(
            num_alumnos=Count("alumnos", distinct=True)
        )

        context["generacion"] = generacion
        context["grupos"] = grupos

        return context


class GrupoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.escuela = kwargs.pop("escuela", None)
        self.generacion = kwargs.pop("generacion", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Grupo
        fields = ["nombre", "fecha_fotografia", "hora_fotografia", "lugar_fotografia"]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "fecha_fotografia": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "hora_fotografia": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control"
            }),
            "lugar_fotografia": forms.TextInput(attrs={
                "class": "form-control"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre")

        if nombre and self.escuela and self.generacion:
            if Grupo.objects.filter(
                nombre=nombre,
                escuela_id=self.escuela,
                generacion_id=self.generacion
            ).exists():
                self.add_error(
                    "nombre",
                    "⚠️ Este grupo ya existe en esta escuela y generación."
                )

        return cleaned_data


class GrupoCreateView(CreateView):
    model = Grupo
    form_class = GrupoForm
    template_name = "escuelas/grupo_form.html"

    # 🔥 Pasar escuela y generación al form correctamente
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["escuela"] = self.kwargs["escuela_id"]
        kwargs["generacion"] = self.kwargs["generacion_id"]
        return kwargs

    # 🔥 Asignar FK antes de guardar
    def form_valid(self, form):
        form.instance.escuela_id = self.kwargs["escuela_id"]
        form.instance.generacion_id = self.kwargs["generacion_id"]
        return super().form_valid(form)

    # 🔥 Redirección después de guardar
    def get_success_url(self):
        return reverse(
            "escuela_detail",
            kwargs={
                "generacion_id": self.kwargs["generacion_id"],
                "pk": self.kwargs["escuela_id"]
            }
        )