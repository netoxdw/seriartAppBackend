from django import forms
from apps.catalogo.models import Modelo
from .models import PedidoItemBase, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago


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


class PedidoItemAnilloForm(forms.ModelForm):

    class Meta:
        model = PedidoItemAnillo
        fields = ["anillo", "tamano_anillo", "cantidad"]

        widgets = {
            "anillo": forms.Select(attrs={"class": "form-control"}),
            "tamano_anillo": forms.NumberInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PedidoItemExtraForm(forms.ModelForm):

    class Meta:
        model = PedidoItemExtra
        fields = ["nombre", "descripcion", "cantidad", "precio_unitario"]

        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ObservacionForm(forms.ModelForm):

    class Meta:
        model = Observacion
        fields = ["texto"]

        widgets = {
            "texto": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Escribe una observación..."
            }),
        }

# PAGO

class PagoForm(forms.ModelForm):

    class Meta:
        model = Pago
        fields = ["fecha_pago", "monto", "folio_nota"]

        widgets = {
            "fecha_pago": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
            "folio_nota": forms.TextInput(attrs={"class": "form-control"}),
        }