
from .models import Generacion, Escuela, Grupo
from django import forms


class GeneracionForm(forms.ModelForm):

    class Meta:
        model = Generacion
        fields = ['nombre_generacion', 'anio']

        widgets = {

            'nombre_generacion': forms.TextInput(attrs={
                'placeholder': 'Ejemplo: Ingeniería 2025'
            }),

            'anio': forms.NumberInput(attrs={
                'placeholder': '2025'
            }),

        }


class EscuelaForm(forms.Form):
    """Agregar una escuela a una generación: elegir una que ya existe o crear una nueva."""

    escuela_existente = forms.ModelChoiceField(
        queryset=Escuela.objects.none(),
        required=False,
        label="Escuela ya registrada",
        empty_label="— No, es una escuela nueva —",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    nombre_escuela = forms.CharField(
        required=False, label="Nombre de la escuela", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. UNAM FES Aragón"}),
    )
    nivel = forms.ChoiceField(
        choices=[("", "— Elige el nivel —")] + Escuela.NIVEL_CHOICES,
        required=False,
        label="Nivel académico",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    direccion = forms.CharField(
        required=False, label="Dirección", max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
    )
    telefono = forms.CharField(
        required=False, label="Teléfono", max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
    )

    def __init__(self, *args, generacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Escuela.objects.order_by("nombre_escuela")
        if generacion is not None:
            qs = qs.exclude(generaciones=generacion)
        self.fields["escuela_existente"].queryset = qs

    def clean(self):
        datos = super().clean()
        if datos.get("escuela_existente"):
            return datos

        nombre = (datos.get("nombre_escuela") or "").strip()
        datos["nombre_escuela"] = nombre
        if not nombre:
            raise forms.ValidationError(
                "Elige una escuela ya registrada o escribe el nombre de la escuela nueva."
            )
        if not datos.get("nivel"):
            self.add_error("nivel", "Elige el nivel académico.")

        repetida = Escuela.objects.filter(nombre_escuela__iexact=nombre).first()
        if repetida:
            if self.fields["escuela_existente"].queryset.filter(pk=repetida.pk).exists():
                self.add_error(
                    "nombre_escuela",
                    f"“{repetida.nombre_escuela}” ya está registrada: selecciónala en la lista de arriba.",
                )
            else:
                self.add_error("nombre_escuela", f"“{repetida.nombre_escuela}” ya está en esta generación.")
        return datos


class EscuelaUpdateForm(forms.ModelForm):

    class Meta:
        model = Escuela
        fields = ["nombre_escuela", "nivel", "direccion", "telefono"]
        labels = {
            "nombre_escuela": "Nombre de la escuela",
            "nivel": "Nivel académico",
            "direccion": "Dirección",
            "telefono": "Teléfono",
        }
        widgets = {
            "nombre_escuela": forms.TextInput(attrs={"class": "form-control"}),
            "nivel": forms.Select(attrs={"class": "form-select"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
        }


class GrupoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.escuela = kwargs.pop("escuela", None)
        self.generacion = kwargs.pop("generacion", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Grupo
        fields = ["nombre_grupo", "fecha_fotografia", "hora_fotografia", "lugar_fotografia"]
        labels = {
            "nombre_grupo": "Nombre del grupo",
            "fecha_fotografia": "Fecha",
            "hora_fotografia": "Hora",
            "lugar_fotografia": "Lugar",
        }

        widgets = {
            "nombre_grupo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej. 6A"
            }),
            "fecha_fotografia": forms.DateInput(format="%Y-%m-%d", attrs={
                "type": "date",
                "class": "form-control"
            }),
            "hora_fotografia": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control"
            }),
            "lugar_fotografia": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej. Auditorio de la escuela"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre_grupo")

        if nombre and self.escuela and self.generacion:
            repetidos = Grupo.objects.filter(
                nombre_grupo__iexact=nombre,
                escuela_id=self.escuela,
                generacion_id=self.generacion
            )
            if self.instance.pk:
                repetidos = repetidos.exclude(pk=self.instance.pk)
            if repetidos.exists():
                self.add_error(
                    "nombre_grupo",
                    "Este grupo ya existe en esta escuela y generación."
                )

        return cleaned_data