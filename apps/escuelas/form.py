
from .models import Generacion, Escuela, Grupo
from django import forms

class EscuelaForm(forms.Form):
    escuela_existente = forms.ModelChoiceField(
        queryset=Escuela.objects.all(),
        required=False,
        label="Escuela existente"
    )

    nombre = forms.CharField(required=False)
    direccion = forms.CharField(required=False)
    telefono = forms.CharField(required=False)


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