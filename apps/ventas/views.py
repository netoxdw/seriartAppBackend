from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView, View
from django.urls import reverse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from apps.alumnos.models import Alumno
from .models import PedidoItemBase, Pedido, PedidoItemAnillo, PedidoItemExtra, Observacion, Pago, PedidoDescuento
from .forms import PedidoItemBaseForm, PedidoItemAnilloForm, PedidoItemExtraForm, ObservacionForm, PagoForm, PedidoDescuentoForm, PedidoCambiarEstadoForm, CapturaFormSet, CapturaAnilloFormSet
from apps.catalogo.models import Producto, Seccion, Tamano, Placa, Anillo, PrecioAnilloGeneracion
from apps.escuelas.models import Escuela
from django.core.exceptions import ValidationError
from django.db import transaction



class PedidoCreateView(LoginRequiredMixin, CreateView):
    model = Pedido
    fields = []
    template_name = "ventas/pedido_form.html"

    def form_valid(self, form):
        form.instance.alumno_id = self.kwargs["alumno_id"]
        return super().form_valid(form)

    def get_success_url(self):
        # Pedido nuevo: directo a la captura rápida de artículos
        return reverse(
            "ventas:pedido_captura",
            kwargs={"pk": self.object.id}
        )
    

class PedidoDetailView(LoginRequiredMixin, DetailView):

    model = Pedido

    template_name = "ventas/pedido_detail.html"

    context_object_name = "pedido"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pedido = self.object

        # ========================================
        # ITEMS
        # ========================================

        items_base = pedido.items_base.select_related(
            "producto__seccion", "producto__modelo", "producto__tamano",
            "producto__color", "producto__variante", "placa"
        )

        items_anillo = pedido.items_anillo.all()

        items_extra = pedido.items_extra.all()

        context["items_base"] = items_base
        context["items_anillo"] = items_anillo
        context["items_extra"] = items_extra

        # ========================================
        # DESCUENTOS
        # ========================================

        descuentos = pedido.descuentos.all()

        total_descuentos = sum(
            d.monto for d in descuentos
        )

        context["descuentos"] = descuentos

        context["total_descuentos"] = total_descuentos

        # ========================================
        # TOTALES
        # ========================================

        total = pedido.total

        total_pagado = pedido.total_pagado

        saldo_pendiente = total - total_pagado

        subtotal = total + total_descuentos

        context["subtotal"] = subtotal

        context["total"] = total

        context["total_pagado"] = total_pagado

        context["saldo_pendiente"] = saldo_pendiente

        # ========================================
        # PORCENTAJE PAGADO
        # ========================================

        if total > 0:

            porcentaje_pagado = (
                total_pagado / total
            ) * 100

        else:

            porcentaje_pagado = 0

        context["porcentaje_pagado"] = round(
            porcentaje_pagado,
            2
        )

        return context


class PedidoEntregaListView(ListView):

    model = Pedido
    template_name = "ventas/pedido_entrega_list.html"
    context_object_name = "pedidos"
    paginate_by = 20

    def get_queryset(self):

        queryset = (
            Pedido.objects
            .select_related("alumno")
            .order_by("-id")
        )

        # =========================
        # FILTRO POR ESTADO
        # =========================

        estado = self.request.GET.get("estado")

        if estado:
            queryset = queryset.filter(estado=estado)

        # =========================
        # BUSCADOR
        # =========================

        q = self.request.GET.get("q")

        if q:
            queryset = queryset.filter(
                Q(id__icontains=q) |
                Q(alumno__nombre__icontains=q) |
                Q(alumno__telefono__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["estado_actual"] = self.request.GET.get("estado", "")
        context["busqueda"] = self.request.GET.get("q", "")

        context["estados"] = [
            ("pendiente", "Pendiente"),
            ("proceso", "En proceso"),
            ("listo", "Listo"),
            ("entregado", "Entregado"),
        ]

        return context

# ############## itembase



# ==============================
# 🧾 CREAR ITEM BASE
# ==============================

class PedidoItemBaseCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        context["pedido"] = pedido
        context["pedido_id"] = pedido.id

        context.update(_contexto_selector(pedido))

        return context

    def get_success_url(self):
        return reverse(
            "ventas:pedido_detail",
            kwargs={"pk": self.kwargs["pedido_id"]}
        )


# ==============================
# 🧩 SELECTOR TAMAÑO → SECCIÓN → PRODUCTO
# ==============================
def _productos_disponibles(generacion_id):
    from apps.escuelas.models import Generacion
    generacion = get_object_or_404(Generacion, id=generacion_id)
    return Producto.con_precio_para(generacion), generacion


def _contexto_selector(pedido, item=None):
    """Tamaños disponibles para la generación del pedido y, al editar, la selección actual."""
    productos, _ = _productos_disponibles(pedido.alumno.grupo.generacion_id)
    tamanos = Tamano.objects.filter(
        activo=True, productos__in=productos
    ).distinct()
    contexto = {"tamanos": tamanos, "pedido": pedido, "pedido_id": pedido.id}
    if item and item.producto_id:
        contexto["tamano_actual"] = item.producto.tamano_id
        contexto["seccion_actual"] = item.producto.seccion_id
        contexto["producto_actual"] = item.producto_id
    return contexto


# ==============================
# ⚡ AJAX → CARGAR SECCIONES
# ==============================
@login_required
def cargar_secciones(request):
    tamano_id = request.GET.get("tamano")
    generacion_id = request.GET.get("generacion")

    if not tamano_id or not generacion_id:
        return JsonResponse([], safe=False)

    productos, _ = _productos_disponibles(generacion_id)
    secciones = Seccion.objects.filter(
        activo=True,
        productos__in=productos.filter(tamano_id=tamano_id),
    ).distinct()

    data = [
        {"id": s.id, "nombre": s.nombre, "lleva_placa": s.lleva_placa}
        for s in secciones
    ]
    return JsonResponse(data, safe=False)


# ==============================
# ⚡ AJAX → CARGAR PRODUCTOS
# ==============================
@login_required
def cargar_productos(request):
    tamano_id = request.GET.get("tamano")
    seccion_id = request.GET.get("seccion")
    generacion_id = request.GET.get("generacion")

    if not tamano_id or not seccion_id or not generacion_id:
        return JsonResponse([], safe=False)

    productos, generacion = _productos_disponibles(generacion_id)
    productos = productos.filter(
        tamano_id=tamano_id, seccion_id=seccion_id
    ).select_related("modelo", "color", "variante")

    data = [
        {
            "id": p.id,
            "nombre": p.descripcion,
            "precio": str(p.precio_para(generacion)),
        }
        for p in productos
    ]
    return JsonResponse(data, safe=False)

# 🔁 REDIRECT ALUMNO → PEDIDO
@login_required
def alumno_pedido_redirect(request, alumno_id):
    alumno = get_object_or_404(
    Alumno,
    id=alumno_id
)

    pedido = Pedido.objects.filter(alumno=alumno).first()

    if not pedido:
        pedido = Pedido.objects.create(alumno=alumno)
        return redirect("ventas:pedido_captura", pk=pedido.id)

    return redirect("ventas:pedido_detail", pk=pedido.id)


# ✏️ UPDATE

class PedidoItemBaseUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemBase
    form_class = PedidoItemBaseForm
    template_name = "ventas/itembase_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_selector(self.object.pedido, self.object))
        return context

    def get_success_url(self):
        return reverse(
            "ventas:pedido_detail",
            kwargs={"pk": self.object.pedido_id}
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.object.pedido
        return kwargs

class PedidoItemBaseDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemBase
    template_name = "ventas/itembase_confirm_delete.html"


    def get_success_url(self):
        return reverse(
            "ventas:pedido_detail",
            kwargs={"pk": self.object.pedido.id}
        )
    
# Anillos ########################################################################333

class PedidoItemAnilloCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemAnillo
    form_class = PedidoItemAnilloForm
    template_name = "ventas/itemanillo_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]  # 🔥 clave
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = Pedido.objects.get(id=self.kwargs["pedido_id"])
        return kwargs

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})
    
class PedidoItemAnilloUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemAnillo
    form_class = PedidoItemAnilloForm
    template_name = "ventas/itemanillo_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id  # 🔥 clave
        return context

    def get_success_url(self):
        return reverse("ventas:ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.object.pedido
        return kwargs


class PedidoItemAnilloDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemAnillo
    template_name = "ventas/itemanillo_confirm_delete.html"

    def get_success_url(self):
        return reverse(
            "ventas:pedido_detail",
            kwargs={"pk": self.object.pedido_id}
        )
    
# EXTRAS #################################################################

# ➕ CREATE
class PedidoItemExtraCreateView(LoginRequiredMixin, CreateView):
    model = PedidoItemExtra
    form_class = PedidoItemExtraForm
    template_name = "ventas/itemextra_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


# ✏️ UPDATE
class PedidoItemExtraUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoItemExtra
    form_class = PedidoItemExtraForm
    template_name = "ventas/itemextra_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})


# 🗑 DELETE
class PedidoItemExtraDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoItemExtra
    template_name = "ventas/itemextra_confirm_delete.html"

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# Observacion ######################################################################

# ➕ CREATE
class ObservacionCreateView(LoginRequiredMixin, CreateView):
    model = Observacion
    form_class = ObservacionForm
    template_name = "ventas/observacion_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


# ✏️ UPDATE
class ObservacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Observacion
    form_class = ObservacionForm
    template_name = "ventas/observacion_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})


# 🗑 DELETE
class ObservacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Observacion
    template_name = "ventas/observacion_confirm_delete.html"

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})


# Pago #####################################################################################

class PagoCreateView(LoginRequiredMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = "ventas/pago_form.html"

    def form_valid(self, form):
        form.instance.pedido_id = self.kwargs["pedido_id"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})


class PagoDeleteView(LoginRequiredMixin, DeleteView):
    model = Pago
    template_name = "ventas/pago_confirm_delete.html"

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})
    

# DESCUENTO ###############################################################################3


# ✅ CREAR
class PedidoDescuentoCreateView(LoginRequiredMixin, CreateView):
    model = PedidoDescuento
    form_class = PedidoDescuentoForm
    template_name = "ventas/descuento_form.html"

    def form_valid(self, form):
        form.instance.pedido = get_object_or_404(
            Pedido, id=self.kwargs["pedido_id"]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.kwargs["pedido_id"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.kwargs["pedido_id"]
        return context


# ✏️ EDITAR
class PedidoDescuentoUpdateView(LoginRequiredMixin, UpdateView):
    model = PedidoDescuento
    form_class = PedidoDescuentoForm
    template_name = "ventas/descuento_form.html"

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido_id"] = self.object.pedido_id
        return context


# 🗑️ ELIMINAR
class PedidoDescuentoDeleteView(LoginRequiredMixin, DeleteView):
    model = PedidoDescuento
    template_name = "ventas/descuento_confirm_delete.html"

    def get_success_url(self):
        return reverse("ventas:pedido_detail", kwargs={"pk": self.object.pedido_id})


# Cambiar estado de panel de entregas

class PedidoCambiarEstadoView(View):

    template_name = "ventas/pedido_cambiar_estado.html"

    def get(self, request, pk):

        pedido = get_object_or_404(
            Pedido,
            pk=pk
        )

        form = PedidoCambiarEstadoForm(
            instance=pedido
        )

        context = {
            "pedido": pedido,
            "form": form,
        }

        return render(
            request,
            self.template_name,
            context
        )

    def post(self, request, pk):

        pedido = get_object_or_404(
            Pedido,
            pk=pk
        )

        form = PedidoCambiarEstadoForm(
            request.POST,
            instance=pedido
        )

        if form.is_valid():

            pedido = form.save(commit=False)

            # =========================
            # FECHA ENTREGA
            # =========================

            if pedido.estado == "entregado":

                if not pedido.fecha_entrega:
                    pedido.fecha_entrega = timezone.now()

            else:

                pedido.fecha_entrega = None
                pedido.recibido_por = None

            pedido.save()

            messages.success(
                request,
                "Estado actualizado correctamente."
            )

            return redirect(
                "ventas:pedido_entrega_list"
            )

        context = {
            "pedido": pedido,
            "form": form,
        }

        return render(
            request,
            self.template_name,
            context
        )

# ==============================
# ⚡ CAPTURA RÁPIDA DE ARTÍCULOS
# Bases (panorámica, diploma, agradecimiento...) y anillos en una sola pantalla.
# Lo que se precarga depende del nivel académico de la escuela.
# ==============================

_PANO = (PedidoItemBase.CONCEPTO_PANORAMICA, "PANORAMICA")
_DIPLOMA = (PedidoItemBase.CONCEPTO_DIPLOMA, "CARTA")
_AGRADEC = (PedidoItemBase.CONCEPTO_AGRADECIMIENTO, "CARTA")

# Nivel de la escuela -> (bases a precargar (concepto, tamaño), ¿precargar anillo?)
CAPTURA_POR_NIVEL = {
    Escuela.NIVEL_SECUNDARIA: ([_PANO], False),
    Escuela.NIVEL_PREPARATORIA: ([_PANO], False),
    Escuela.NIVEL_UNIVERSIDAD: ([_PANO, _DIPLOMA, _AGRADEC], True),
    Escuela.NIVEL_OTRO: ([_PANO, _DIPLOMA, _AGRADEC], False),
}


def _anillos_con_precio(generacion):
    precios = {
        p.anillo_id: p.precio
        for p in PrecioAnilloGeneracion.objects.filter(generacion=generacion, anillo__activo=True)
    }
    return Anillo.objects.filter(id__in=precios), precios


def _catalogo_captura(generacion):
    """Todo el catálogo disponible para la generación, para que el selector sea instantáneo."""
    productos = Producto.con_precio_para(generacion).select_related(
        "seccion", "modelo", "tamano", "color", "variante"
    )
    anillos, precios_anillo = _anillos_con_precio(generacion)
    data_productos = [
        {
            "id": p.id,
            "seccion": p.seccion_id,
            "tamano": p.tamano_id,
            "modelo": p.modelo_id,
            "color": p.color_id,
            "variante": p.variante_id,
            "nombre": p.descripcion,
            "precio": str(p.precio_para(generacion)),
        }
        for p in productos
    ]
    tamanos_ids = {p["tamano"] for p in data_productos}
    secciones_ids = {p["seccion"] for p in data_productos}
    return productos, anillos, {
        "productos": data_productos,
        "tamanos": [
            {"id": t.id, "nombre": t.nombre}
            for t in Tamano.objects.filter(id__in=tamanos_ids)
        ],
        "secciones": [
            {"id": s.id, "nombre": s.nombre, "lleva_placa": s.lleva_placa}
            for s in Seccion.objects.filter(id__in=secciones_ids)
        ],
        "placas": [
            {"id": p.id, "nombre": p.nombre}
            for p in Placa.objects.filter(activo=True)
        ],
        "conceptos": [
            {"id": k, "nombre": v} for k, v in PedidoItemBase.CONCEPTO_CHOICES
        ],
        "anillos": [
            {"id": a.id, "nombre": f"{a.modelo} · {a.metal}", "precio": str(precios_anillo[a.id])}
            for a in anillos
        ],
    }


def _filas_iniciales(pedido):
    """Precarga según el nivel de la escuela, sin repetir lo que el pedido ya tiene."""
    nivel = pedido.alumno.grupo.escuela.nivel
    bases, con_anillo = CAPTURA_POR_NIVEL.get(nivel, CAPTURA_POR_NIVEL[Escuela.NIVEL_OTRO])
    existentes = set(pedido.items_base.values_list("concepto", flat=True))
    tamanos = {t.nombre: t.id for t in Tamano.objects.all()}

    filas = [
        {"concepto": concepto, "tamano": tamanos.get(tamano), "cantidad": 1}
        for concepto, tamano in bases
        if concepto not in existentes
    ]
    anillos = (
        [{"cantidad": 1}]
        if con_anillo and not pedido.items_anillo.exists()
        else []
    )
    if not filas and not anillos:
        filas = [{"concepto": PedidoItemBase.CONCEPTO_OTRO, "tamano": None, "cantidad": 1}]
    return filas, anillos


def _errores(form):
    return [str(e) for errs in form.errors.values() for e in errs]


def _filas_desde_formset(formset, productos):
    """Reconstruye las filas tras un error para no perder lo capturado."""
    tamano_de = {p.id: p.tamano_id for p in productos}
    filas = []
    for form in formset:
        producto = form.data.get(form.add_prefix("producto")) or ""
        producto = int(producto) if producto.isdigit() else None
        filas.append({
            "concepto": form.data.get(form.add_prefix("concepto"), PedidoItemBase.CONCEPTO_OTRO),
            "tamano": tamano_de.get(producto),
            "producto": producto,
            "placa": form.data.get(form.add_prefix("placa")) or None,
            "color_placa": form.data.get(form.add_prefix("color_placa"), ""),
            "cantidad": form.data.get(form.add_prefix("cantidad"), 1),
            "errores": _errores(form),
        })
    return filas


def _anillos_desde_formset(formset):
    filas = []
    for form in formset:
        anillo = form.data.get(form.add_prefix("anillo")) or ""
        filas.append({
            "anillo": int(anillo) if anillo.isdigit() else None,
            "tamano_anillo": form.data.get(form.add_prefix("tamano_anillo"), ""),
            "cantidad": form.data.get(form.add_prefix("cantidad"), 1),
            "errores": _errores(form),
        })
    return filas


@login_required
def pedido_captura(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("alumno__grupo__generacion", "alumno__grupo__escuela"),
        pk=pk,
    )
    generacion = pedido.alumno.grupo.generacion
    productos, anillos, catalogo = _catalogo_captura(generacion)
    error_general = None

    if request.method == "POST":
        formset = CapturaFormSet(request.POST, form_kwargs={"productos": productos})
        formset_anillos = CapturaAnilloFormSet(
            request.POST, prefix="anillo", form_kwargs={"anillos": anillos}
        )
        if formset.is_valid() and formset_anillos.is_valid():
            bases = [f.cleaned_data for f in formset if f.cleaned_data.get("producto")]
            aros = [f.cleaned_data for f in formset_anillos if f.cleaned_data.get("anillo")]
            if not bases and not aros:
                error_general = "Selecciona al menos un artículo."
            else:
                try:
                    with transaction.atomic():
                        for datos in bases:
                            item = PedidoItemBase(
                                pedido=pedido,
                                concepto=datos["concepto"],
                                producto=datos["producto"],
                                placa=datos.get("placa"),
                                color_placa=datos.get("color_placa") or None,
                                cantidad=datos["cantidad"],
                            )
                            item.full_clean()
                            item.save()
                        for datos in aros:
                            item = PedidoItemAnillo(
                                pedido=pedido,
                                anillo=datos["anillo"],
                                tamano_anillo=datos["tamano_anillo"],
                                cantidad=datos["cantidad"],
                            )
                            item.full_clean()
                            item.save()
                except ValidationError as exc:
                    error_general = " ".join(exc.messages)
                else:
                    total = len(bases) + len(aros)
                    messages.success(request, f"Se agregaron {total} artículo(s) al pedido.")
                    return redirect("ventas:pedido_detail", pk=pedido.pk)
        else:
            errores = list(formset.non_form_errors()) + list(formset_anillos.non_form_errors())
            error_general = " ".join(str(e) for e in errores) or None
        filas = _filas_desde_formset(formset, productos)
        filas_anillo = _anillos_desde_formset(formset_anillos)
    else:
        filas, filas_anillo = _filas_iniciales(pedido)

    return render(request, "ventas/pedido_captura.html", {
        "pedido": pedido,
        "catalogo": catalogo,
        "filas": filas,
        "filas_anillo": filas_anillo,
        "error_general": error_general,
        "items_existentes": pedido.items_base.select_related(
            "producto__seccion", "producto__modelo", "producto__tamano",
            "producto__color", "producto__variante",
        ),
        "anillos_existentes": pedido.items_anillo.select_related("anillo"),
    })
