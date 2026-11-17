from django import forms
from .models import Alumno

class AlumnoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.grupo_id = kwargs.pop("grupo_id", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Alumno
        fields = ["nombre_alumno", "telefono", "folio_fotos"]

        widgets = {
            "nombre_alumno": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "folio_fotos": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre_alumno")

        if nombre and self.grupo_id:
            if Alumno.objects.filter(
                nombre_alumno=nombre,
                grupo_id=self.grupo_id
            ).exclude(id=self.instance.id).exists():

                self.add_error(
                    "nombre_alumno",
                    "⚠️ Este alumno ya existe en este grupo."
                )

        return cleaned_data