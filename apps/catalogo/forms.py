import re

from django import forms

from apps.escuelas.models import Generacion

from .models import Color, Modelo, Placa, Seccion, Tamano, Variante


def _mayusculas(texto):
    """El importador compara nombres en MAYÚSCULAS; se guardan igual para no duplicar."""
    return re.sub(r"\s+", " ", texto or "").strip().upper()


class _NombreMayusculasMixin:
    def clean_nombre(self):
        return _mayusculas(self.cleaned_data.get("nombre"))


# ---------------------------------------------------------------------------
# Dimensiones (tablas editables en el panel)
# ---------------------------------------------------------------------------

_W_TEXTO = forms.TextInput(attrs={"class": "form-control form-control-sm"})
_W_NUM = forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "max-width:90px"})
_W_CHECK = forms.CheckboxInput(attrs={"class": "form-check-input"})


class SeccionForm(_NombreMayusculasMixin, forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ["nombre", "lleva_placa", "orden", "activo"]
        widgets = {"nombre": _W_TEXTO, "lleva_placa": _W_CHECK, "orden": _W_NUM, "activo": _W_CHECK}


class TamanoForm(_NombreMayusculasMixin, forms.ModelForm):
    class Meta:
        model = Tamano
        fields = ["nombre", "concepto", "orden", "activo"]
        widgets = {
            "nombre": _W_TEXTO,
            "concepto": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "orden": _W_NUM,
            "activo": _W_CHECK,
        }


class ModeloForm(_NombreMayusculasMixin, forms.ModelForm):
    class Meta:
        model = Modelo
        fields = ["nombre", "activo"]
        widgets = {"nombre": _W_TEXTO, "activo": _W_CHECK}


class ColorForm(_NombreMayusculasMixin, forms.ModelForm):
    class Meta:
        model = Color
        fields = ["nombre", "activo"]
        widgets = {"nombre": _W_TEXTO, "activo": _W_CHECK}


class VarianteForm(_NombreMayusculasMixin, forms.ModelForm):
    class Meta:
        model = Variante
        fields = ["nombre", "activo"]
        widgets = {"nombre": _W_TEXTO, "activo": _W_CHECK}


class PlacaForm(forms.ModelForm):
    class Meta:
        model = Placa
        fields = ["nombre", "orden", "activo"]
        widgets = {"nombre": _W_TEXTO, "orden": _W_NUM, "activo": _W_CHECK}


# clave de URL -> (modelo, form, título, descripción)
DIMENSIONES = {
    "secciones": (Seccion, SeccionForm, "Secciones",
                  "Líneas de producto. 'Lleva placa' muestra el tipo y color de placa al capturar."),
    "tamanos": (Tamano, TamanoForm, "Tamaños",
                "El orden define las columnas de la tabla de precios. El concepto decide si en la "
                "captura se ofrece como diploma/agradecimiento o como foto panorámica."),
    "modelos": (Modelo, ModeloForm, "Modelos", "Un modelo puede estar en varias secciones."),
    "colores": (Color, ColorForm, "Colores", "Color del marco."),
    "variantes": (Variante, VarianteForm, "Variantes", "Pueden tener precio propio (ej. ESCULTURAS)."),
    "placas": (Placa, PlacaForm, "Placas", "Tipos de placa que se ofrecen al capturar."),
}


# ---------------------------------------------------------------------------
# Alta masiva de productos
# ---------------------------------------------------------------------------

class AltaProductosForm(forms.Form):
    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.all(), label="Sección",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    modelo = forms.ModelChoiceField(
        queryset=Modelo.objects.all(), required=False, label="Modelo existente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    modelo_nuevo = forms.CharField(
        required=False, max_length=100, label="…o modelo nuevo",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. VENECIA"}),
    )
    tamanos = forms.ModelMultipleChoiceField(
        queryset=Tamano.objects.filter(activo=True), label="Tamaños",
        widget=forms.CheckboxSelectMultiple,
    )
    colores = forms.ModelMultipleChoiceField(
        queryset=Color.objects.filter(activo=True), required=False, label="Colores (opcional)",
        widget=forms.CheckboxSelectMultiple,
    )
    variantes = forms.ModelMultipleChoiceField(
        queryset=Variante.objects.filter(activo=True), required=False, label="Variantes (opcional)",
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        datos = super().clean()
        nuevo = _mayusculas(datos.get("modelo_nuevo"))
        if datos.get("modelo") and nuevo:
            raise forms.ValidationError("Elige un modelo existente o escribe uno nuevo, no ambos.")
        if not datos.get("modelo") and not nuevo:
            raise forms.ValidationError("Elige un modelo existente o escribe uno nuevo.")
        if nuevo:
            existente = Modelo.objects.filter(nombre=nuevo).first()
            if existente:
                datos["modelo"] = existente  # ya existía: se reutiliza
            datos["modelo_nuevo"] = nuevo
        return datos


# ---------------------------------------------------------------------------
# Copiar precios entre generaciones
# ---------------------------------------------------------------------------

REDONDEO_CHOICES = [
    ("0", "Sin redondear"),
    ("10", "A múltiplos de $10"),
    ("50", "A múltiplos de $50"),
    ("100", "A múltiplos de $100"),
]


class CopiarPreciosForm(forms.Form):
    origen = forms.ModelChoiceField(
        queryset=Generacion.objects.all(), label="Copiar desde",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    destino = forms.ModelChoiceField(
        queryset=Generacion.objects.all(), required=False, label="Hacia generación existente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    destino_anio = forms.IntegerField(
        required=False, min_value=2000, max_value=2100, label="…o crear generación nueva (año)",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ej. 2028"}),
    )
    aumento = forms.DecimalField(
        initial=0, max_digits=6, decimal_places=2, min_value=-90, max_value=500,
        label="Aumento (%)", widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
    )
    redondeo = forms.ChoiceField(
        choices=REDONDEO_CHOICES, initial="0", label="Redondeo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sobrescribir = forms.BooleanField(
        required=False, label="Sobrescribir precios que ya existan en el destino",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        datos = super().clean()
        destino, anio = datos.get("destino"), datos.get("destino_anio")
        if destino and anio:
            raise forms.ValidationError("Elige una generación existente o escribe un año nuevo, no ambos.")
        if not destino and not anio:
            raise forms.ValidationError("Indica la generación destino.")
        if anio:
            existente = Generacion.objects.filter(anio=anio).first()
            if existente:
                datos["destino"] = existente
        origen = datos.get("origen")
        if origen and (datos.get("destino") == origen or (anio and origen.anio == anio)):
            raise forms.ValidationError("El origen y el destino deben ser distintos.")
        return datos


# ---------------------------------------------------------------------------
# Subir el Excel
# ---------------------------------------------------------------------------

class ImportarExcelForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo .xlsx",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".xlsx"}),
    )
    anio = forms.IntegerField(
        required=False, min_value=2000, max_value=2100, label="Generación (año)",
        help_text="Déjalo vacío para leerlo del encabezado 'PRECIO <año>'.",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Automático"}),
    )

    def clean_archivo(self):
        f = self.cleaned_data["archivo"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Sube un archivo .xlsx.")
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo pesa más de 5 MB.")
        return f
