from django import forms
from django.forms import inlineformset_factory

from .models import PagoPedidoVario, PedidoVario, ProductoPedidoVario

_FECHA = {"type": "date", "class": "form-control"}


class PedidoVarioForm(forms.ModelForm):
    anticipo = forms.DecimalField(
        label="Anticipo", required=False, min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "0.00"}),
        help_text="Si el cliente deja un pago al hacer el pedido, se registra aquí.",
    )
    forma_anticipo = forms.ChoiceField(
        label="Forma de pago", choices=PagoPedidoVario.FORMAS, required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = PedidoVario
        fields = ["cliente", "telefono", "fecha_entrega", "estado", "notas"]
        widgets = {
            "cliente": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del cliente", "autofocus": True}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
            "fecha_entrega": forms.DateInput(attrs=_FECHA, format="%Y-%m-%d"),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Indicaciones generales del pedido (opcional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # El anticipo solo se captura al crear; después se usan los pagos
            del self.fields["anticipo"]
            del self.fields["forma_anticipo"]
        else:
            # Al crear, el estado sale del anticipo
            del self.fields["estado"]


class ProductoForm(forms.ModelForm):
    class Meta:
        model = ProductoPedidoVario
        fields = ["producto", "descripcion", "cantidad", "precio_unitario", "fecha_elaboracion"]
        widgets = {
            "producto": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Playera estampada", "data-campo": "producto"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 1, "placeholder": "Talla, color, diseño, medidas…"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1", "data-campo": "cantidad"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "0.00", "data-campo": "precio"}),
            "fecha_elaboracion": forms.DateInput(attrs=_FECHA, format="%Y-%m-%d"),
        }


ProductoFormSet = inlineformset_factory(
    PedidoVario, ProductoPedidoVario, form=ProductoForm,
    extra=0, min_num=1, validate_min=True, can_delete=True,
)


class PagoForm(forms.ModelForm):
    class Meta:
        model = PagoPedidoVario
        fields = ["monto", "fecha", "forma_pago", "referencia"]
        widgets = {
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "autofocus": True}),
            "fecha": forms.DateInput(attrs=_FECHA, format="%Y-%m-%d"),
            "forma_pago": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control", "placeholder": "Opcional"}),
        }
