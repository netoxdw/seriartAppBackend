from django import forms
from apps.catalogo.models import Modelo, Anillo, PrecioBaseGeneracion
from .models import PedidoItemBase, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento

# apps/ventas/forms.py

class PedidoItemBaseForm(forms.ModelForm):

    class Meta:
        model = PedidoItemBase
        fields = ["modelo", "placa", "color_placa", "cantidad"]

    def __init__(self, *args, **kwargs):
        pedido = kwargs.pop("pedido", None)
        super().__init__(*args, **kwargs)

        if pedido:
            generacion = pedido.alumno.grupo.generacion

            modelos_ids = PrecioBaseGeneracion.objects.filter(
                generacion=generacion
            ).values_list("modelo_id", flat=True)

            self.fields["modelo"].queryset = Modelo.objects.filter(
                id__in=modelos_ids
            )
        else:
            self.fields["modelo"].queryset = Modelo.objects.none()





class PedidoItemAnilloForm(forms.ModelForm):

    class Meta:
        model = PedidoItemAnillo
        fields = ["anillo", "tamano_anillo", "cantidad"]

    def __init__(self, *args, **kwargs):
        pedido = kwargs.pop("pedido", None)
        super().__init__(*args, **kwargs)

        from apps.catalogo.models import PrecioAnilloGeneracion

        if pedido:
            generacion = pedido.alumno.grupo.generacion

            anillos_ids = PrecioAnilloGeneracion.objects.filter(
                generacion=generacion
            ).values_list("anillo_id", flat=True)

            self.fields["anillo"].queryset = Anillo.objects.filter(
                id__in=anillos_ids
            )


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



class PedidoDescuentoForm(forms.ModelForm):
    class Meta:
        model = PedidoDescuento
        fields = ["monto", "motivo"]

        widgets = {
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
            "motivo": forms.TextInput(attrs={"class": "form-control"}),
        }