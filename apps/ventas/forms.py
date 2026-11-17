from django import forms
from apps.catalogo.models import Producto, Placa, Anillo
from .models import Pedido, PedidoItemBase, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento

# apps/ventas/forms.py

class PedidoItemBaseForm(forms.ModelForm):

    class Meta:
        model = PedidoItemBase
        fields = ["concepto", "producto", "placa", "color_placa", "cantidad"]

    def __init__(self, *args, **kwargs):
        pedido = kwargs.pop("pedido", None)
        super().__init__(*args, **kwargs)

        if pedido:
            # El modelo valida contra el pedido (precio por generación)
            self.instance.pedido = pedido
            generacion = pedido.alumno.grupo.generacion
            self.fields["producto"].queryset = Producto.con_precio_para(
                generacion
            ).select_related("seccion", "modelo", "tamano", "color", "variante")
        else:
            self.fields["producto"].queryset = Producto.objects.none()

        self.fields["placa"].queryset = Placa.objects.filter(activo=True)


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

class PedidoCambiarEstadoForm(forms.ModelForm):

    class Meta:

        model = Pedido

        fields = [
            "estado",
            "recibido_por",
            "notas_entrega",
        ]

        widgets = {

            "estado": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "recibido_por": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de quien recibe"
                }
            ),

            "notas_entrega": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Notas adicionales"
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        estado = cleaned_data.get("estado")
        recibido_por = cleaned_data.get("recibido_por")

        # =========================
        # VALIDAR ENTREGA
        # =========================

        if estado == "entregado" and not recibido_por:

            self.add_error(
                "recibido_por",
                "Debes indicar quién recibe el pedido."
            )

        return cleaned_data

# ==============================
# ⚡ CAPTURA RÁPIDA DE ITEMS BASE
# ==============================

class CapturaItemForm(forms.Form):
    """Una fila de la captura rápida. Las filas sin producto se ignoran."""

    concepto = forms.ChoiceField(choices=PedidoItemBase.CONCEPTO_CHOICES)
    producto = forms.ModelChoiceField(queryset=Producto.objects.none(), required=False)
    placa = forms.ModelChoiceField(queryset=Placa.objects.none(), required=False)
    color_placa = forms.CharField(max_length=50, required=False)
    cantidad = forms.IntegerField(min_value=1, max_value=99, initial=1)

    def __init__(self, *args, productos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = productos if productos is not None else Producto.objects.none()
        self.fields["placa"].queryset = Placa.objects.filter(activo=True)


CapturaFormSet = forms.formset_factory(CapturaItemForm, extra=0, max_num=30, validate_max=True)


class CapturaAnilloForm(forms.Form):
    """Una fila de anillo en la captura rápida. Las filas sin anillo se ignoran."""

    anillo = forms.ModelChoiceField(queryset=Anillo.objects.none(), required=False)
    tamano_anillo = forms.DecimalField(
        max_digits=4, decimal_places=1, min_value=1, max_value=20, required=False
    )
    cantidad = forms.IntegerField(min_value=1, max_value=99, initial=1)

    def __init__(self, *args, anillos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["anillo"].queryset = anillos if anillos is not None else Anillo.objects.none()

    def clean(self):
        datos = super().clean()
        if datos.get("anillo") and datos.get("tamano_anillo") is None:
            self.add_error("tamano_anillo", "Indica la talla del anillo.")
        return datos


CapturaAnilloFormSet = forms.formset_factory(CapturaAnilloForm, extra=0, max_num=10, validate_max=True)
