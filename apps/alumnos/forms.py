from django import forms
from .models import Alumno


class AlumnoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.grupo_id = kwargs.pop("grupo_id", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Alumno
        fields = ["nombre_alumno", "telefono", "folio_fotos"]
        labels = {
            "nombre_alumno": "Nombre completo",
            "telefono": "Teléfono",
            "folio_fotos": "Folio de fotos",
        }
        help_texts = {
            "nombre_alumno": "",
            "folio_fotos": "",
        }
        widgets = {
            "nombre_alumno": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Ej. Ana López García", "autofocus": True,
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control", "type": "tel", "inputmode": "tel",
                "placeholder": "Opcional", "autocomplete": "off",
            }),
            "folio_fotos": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Opcional. Ej. 1234 o 1234-1236",
            }),
        }

    def clean_nombre_alumno(self):
        # Quita espacios dobles y al inicio/fin
        return " ".join((self.cleaned_data.get("nombre_alumno") or "").split())

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre_alumno")

        if nombre and self.grupo_id:
            if Alumno.objects.filter(
                nombre_alumno__iexact=nombre,
                grupo_id=self.grupo_id
            ).exclude(id=self.instance.id).exists():

                self.add_error(
                    "nombre_alumno",
                    "Ya hay un alumno con este nombre en el grupo. Búscalo en la lista del grupo."
                )

        return cleaned_data
