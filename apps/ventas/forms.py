from django import forms
from apps.catalogo.models import Modelo
from .models import PedidoItemBase


class PedidoItemBaseForm(forms.ModelForm):

    class Meta:
        model = PedidoItemBase
        fields = ["modelo", "placa", "color_placa", "cantidad"]

        widgets = {
            "modelo": forms.Select(attrs={"class": "form-control"}),
            "placa": forms.Select(attrs={"class": "form-control"}),
            "color_placa": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
        }