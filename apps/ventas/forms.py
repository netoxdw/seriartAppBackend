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

# ==============================
# 🚦 CAMBIOS DE ESTADO DEL PEDIDO (staff)
# ==============================

_NOTA = forms.CharField(
    required=False, max_length=500, label="Nota (opcional)",
    widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
)


class MarcarListoForm(forms.Form):
    nota = _NOTA
    confirmar_anticipo = forms.BooleanField(
        required=False,
        label="Confirmo marcarlo como listo aunque el anticipo es menor al 50 %",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido

    def clean(self):
        datos = super().clean()
        if self.pedido and not self.pedido.anticipo_suficiente and not datos.get("confirmar_anticipo"):
            self.add_error("confirmar_anticipo", "El anticipo es menor al 50 %: confirma para continuar.")
        return datos


class MarcarEntregadoForm(forms.Form):
    recibido_por = forms.CharField(
        max_length=150, label="Recibido por",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de quien recibe"}),
        error_messages={"required": "Indica quién recibe el pedido."},
    )
    nota = _NOTA
    confirmar_saldo = forms.BooleanField(
        required=False,
        label="Confirmo la entrega aunque tiene saldo pendiente",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido

    def clean(self):
        datos = super().clean()
        if self.pedido and self.pedido.saldo_pendiente > 0 and not datos.get("confirmar_saldo"):
            self.add_error("confirmar_saldo", "Tiene saldo pendiente: confirma para entregar.")
        return datos


class DevolucionForm(forms.Form):
    motivo = forms.CharField(
        max_length=1000, label="Motivo de la devolución",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3,
                                     "placeholder": "Ej. marco dañado, nombre mal escrito, foto equivocada…"}),
        error_messages={"required": "Escribe el motivo de la devolución."},
    )


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
