from django import forms
from .models import Alumno

class AlumnoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.grupo_id = kwargs.pop("grupo_id", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Alumno
        fields = ["nombre", "telefono", "folio_fotos"]

        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "folio_fotos": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre")

        if nombre and self.grupo_id:
            if Alumno.objects.filter(
                nombre=nombre,
                grupo_id=self.grupo_id
            ).exclude(id=self.instance.id).exists():

                self.add_error(
                    "nombre",
                    "⚠️ Este alumno ya existe en este grupo."
                )

        return cleaned_data