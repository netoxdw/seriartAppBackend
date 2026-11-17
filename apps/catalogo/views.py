"""
Panel de catálogo: precios, productos, anillos, dimensiones y herramientas.
Solo para usuarios staff.
"""
import itertools
import os
import tempfile
import uuid
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.forms import modelformset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.escuelas.models import Generacion

from .forms import (
    DIMENSIONES,
    AltaProductosForm,
    CopiarPreciosForm,
    ImportarExcelForm,
)
from .importador import ImportacionError, importar_catalogo
from .models import (
    Anillo,
    Modelo,
    PrecioAnilloGeneracion,
    PrecioBase,
    PrecioEspecial,
    Producto,
    Seccion,
    Tamano,
    Variante,
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def staff_required(vista):
    """Requiere sesión iniciada y usuario staff."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Solo el personal autorizado puede modificar el catálogo.")
        return vista(request, *args, **kwargs)

    return envoltura


def _generacion(request):
    """Generación elegida (?generacion=ID) o la más reciente."""
    gen_id = request.POST.get("generacion") or request.GET.get("generacion")
    if gen_id and str(gen_id).isdigit():
        gen = Generacion.objects.filter(pk=gen_id).first()
        if gen:
            return gen
    return Generacion.objects.order_by("-anio").first()


def _contexto(request, tab, generacion=None, **extra):
    contexto = {
        "tab": tab,
        "generaciones": Generacion.objects.order_by("-anio"),
        "generacion": generacion,
    }
    contexto.update(extra)
    return contexto


def _decimal(texto):
    """'1,250.50' -> Decimal; '' -> None; inválido o <= 0 -> ValueError."""
    texto = (texto or "").strip().replace(",", "").replace("$", "")
    if not texto:
        return None
    try:
        valor = Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(texto) from exc
    if valor <= 0:
        raise ValueError(texto)
    return valor


def _mapa_precios(generacion):
    """Función producto -> precio (o None) sin consultas por producto."""
    if generacion is None:
        return lambda p: None
    base = {
        (s, t, v): precio
        for s, t, v, precio in PrecioBase.objects.filter(generacion=generacion)
        .values_list("seccion_id", "tamano_id", "variante_id", "precio")
    }
    especiales = dict(
        PrecioEspecial.objects.filter(generacion=generacion).values_list("producto_id", "precio")
    )

    def precio(p):
        if p.id in especiales:
            return especiales[p.id]
        if p.variante_id and (p.seccion_id, p.tamano_id, p.variante_id) in base:
            return base[(p.seccion_id, p.tamano_id, p.variante_id)]
        return base.get((p.seccion_id, p.tamano_id, None))

    return precio


def _url(nombre, generacion=None, **params):
    if generacion:
        params["generacion"] = generacion.pk
    params = {k: v for k, v in params.items() if v not in (None, "")}
    return reverse(nombre) + (f"?{urlencode(params)}" if params else "")


@staff_required
def panel(request):
    return redirect("catalogo:precios")


# ---------------------------------------------------------------------------
# Precios de bases (tabla Sección × Tamaño) y precios especiales
# ---------------------------------------------------------------------------

def _tabla_precios(generacion, enviados=None, errores=()):
    """Filas: una por sección (+ una por variante si la sección tiene variantes)."""
    tamanos = list(Tamano.objects.filter(productos__isnull=False).distinct().order_by("orden", "nombre"))
    secciones = list(Seccion.objects.filter(productos__isnull=False).distinct().order_by("orden", "nombre"))
    combos = set(Producto.objects.values_list("seccion_id", "tamano_id"))
    variantes_por_seccion = {}
    for s_id, v_id in Producto.objects.exclude(variante=None).values_list("seccion_id", "variante_id").distinct():
        variantes_por_seccion.setdefault(s_id, set()).add(v_id)
    nombres_variante = dict(Variante.objects.values_list("id", "nombre"))
    actuales = {
        (s, t, v or 0): precio
        for s, t, v, precio in PrecioBase.objects.filter(generacion=generacion)
        .values_list("seccion_id", "tamano_id", "variante_id", "precio")
    }

    filas = []
    for s in secciones:
        variantes = sorted(variantes_por_seccion.get(s.id, []), key=lambda v: nombres_variante[v])
        grupo = [0] + variantes
        for i, v in enumerate(grupo):
            celdas = []
            for t in tamanos:
                nombre = f"p-{s.id}-{v}-{t.id}"
                if enviados is not None:
                    valor = enviados.get(nombre, "")
                else:
                    actual = actuales.get((s.id, t.id, v))
                    valor = f"{actual:.2f}" if actual is not None else ""
                celdas.append({
                    "nombre": nombre,
                    "valor": valor,
                    "disponible": (s.id, t.id) in combos,
                    "error": nombre in errores,
                })
            filas.append({
                "seccion": s,
                "variante": nombres_variante.get(v) if v else None,
                "tiene_variantes": bool(variantes),
                "primera": i == 0,
                "rowspan": len(grupo),
                "celdas": celdas,
            })
    return tamanos, filas


def _guardar_precios_base(request, generacion):
    combos = set(Producto.objects.values_list("seccion_id", "tamano_id"))
    validos_s = set(Seccion.objects.values_list("id", flat=True))
    validos_t = set(Tamano.objects.values_list("id", flat=True))
    validos_v = set(Variante.objects.values_list("id", flat=True)) | {0}
    cambios, errores = [], []
    for clave, texto in request.POST.items():
        if not clave.startswith("p-"):
            continue
        try:
            _, s, v, t = clave.split("-")
            s, v, t = int(s), int(v), int(t)
        except ValueError:
            continue
        if s not in validos_s or t not in validos_t or v not in validos_v or (s, t) not in combos:
            continue
        try:
            cambios.append((s, v or None, t, _decimal(texto)))
        except ValueError:
            errores.append(clave)
    if errores:
        return 0, errores

    n = 0
    with transaction.atomic():
        for s, v, t, precio in cambios:
            filtro = dict(generacion=generacion, seccion_id=s, tamano_id=t, variante_id=v)
            existente = PrecioBase.objects.filter(**filtro).first()
            if precio is None:
                if existente:
                    existente.delete()
                    n += 1
            elif existente is None:
                PrecioBase.objects.create(precio=precio, **filtro)
                n += 1
            elif existente.precio != precio:
                existente.precio = precio
                existente.save(update_fields=["precio"])
                n += 1
    return n, []


def _guardar_especiales(request, generacion):
    n, errores = 0, []
    with transaction.atomic():
        for esp in PrecioEspecial.objects.filter(generacion=generacion):
            if request.POST.get(f"edel-{esp.id}"):
                esp.delete()
                n += 1
                continue
            if f"e-{esp.id}" not in request.POST:
                continue  # no venía en el formulario: no se toca
            try:
                precio = _decimal(request.POST.get(f"e-{esp.id}"))
            except ValueError:
                errores.append(f"Precio especial inválido para {esp.producto}.")
                continue
            if precio is None:
                esp.delete()
                n += 1
            elif precio != esp.precio:
                esp.precio = precio
                esp.save(update_fields=["precio"])
                n += 1

        prod_id = request.POST.get("nuevo_producto")
        texto = request.POST.get("nuevo_precio")
        if prod_id or (texto or "").strip():
            producto = Producto.objects.filter(pk=prod_id).first() if str(prod_id).isdigit() else None
            try:
                precio = _decimal(texto)
            except ValueError:
                precio = None
            if not producto or precio is None:
                errores.append("Para agregar un precio especial elige el producto y escribe un precio mayor a cero.")
            else:
                PrecioEspecial.objects.update_or_create(
                    generacion=generacion, producto=producto, defaults={"precio": precio}
                )
                n += 1
    return n, errores


@staff_required
def precios(request):
    generacion = _generacion(request)
    if generacion is None:
        messages.warning(request, "Primero crea una generación.")
        return redirect("generacion_create")

    enviados, errores_celdas = None, []
    if request.method == "POST":
        n_base, errores_celdas = _guardar_precios_base(request, generacion)
        if errores_celdas:
            enviados = request.POST
            messages.error(request, "Hay precios inválidos (marcados en rojo). No se guardó nada de la tabla.")
        else:
            n_esp, errores_esp = _guardar_especiales(request, generacion)
            for e in errores_esp:
                messages.error(request, e)
            if n_base or n_esp:
                messages.success(request, f"Se guardaron {n_base + n_esp} cambio(s) de precios para {generacion.anio}.")
            elif not errores_esp:
                messages.info(request, "No hubo cambios.")
            return redirect(_url("catalogo:precios", generacion))

    tamanos, filas = _tabla_precios(generacion, enviados, errores_celdas)
    precio_de = _mapa_precios(generacion)
    productos = list(
        Producto.objects.filter(activo=True).select_related("seccion", "modelo", "tamano", "color", "variante")
    )
    sin_precio = [p for p in productos if precio_de(p) is None]
    return render(request, "catalogo/precios.html", _contexto(
        request, "precios", generacion,
        tamanos=tamanos,
        filas=filas,
        especiales=PrecioEspecial.objects.filter(generacion=generacion).select_related(
            "producto__seccion", "producto__modelo", "producto__tamano", "producto__color", "producto__variante"
        ),
        productos=productos,
        sin_precio=sin_precio,
    ))


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

@staff_required
def productos(request):
    generacion = _generacion(request)
    filtros = {
        "seccion": request.GET.get("seccion", ""),
        "tamano": request.GET.get("tamano", ""),
        "estado": request.GET.get("estado", "activos"),
        "q": request.GET.get("q", "").strip(),
    }

    if request.method == "POST":
        producto = get_object_or_404(Producto, pk=request.POST.get("producto"))
        accion = request.POST.get("accion")
        if accion == "toggle":
            producto.activo = not producto.activo
            producto.save(update_fields=["activo"])
            estado = "activado" if producto.activo else "desactivado"
            messages.success(request, f"{producto} {estado}.")
        elif accion == "eliminar":
            try:
                with transaction.atomic():
                    PrecioEspecial.objects.filter(producto=producto).delete()
                    producto.delete()
                messages.success(request, f"{producto} eliminado.")
            except ProtectedError:
                messages.error(request, f"{producto} ya se usó en pedidos: no se puede eliminar, desactívalo.")
        return redirect(request.get_full_path())

    qs = Producto.objects.select_related("seccion", "modelo", "tamano", "color", "variante")
    if filtros["seccion"].isdigit():
        qs = qs.filter(seccion_id=filtros["seccion"])
    if filtros["tamano"].isdigit():
        qs = qs.filter(tamano_id=filtros["tamano"])
    if filtros["estado"] == "activos":
        qs = qs.filter(activo=True)
    elif filtros["estado"] == "inactivos":
        qs = qs.filter(activo=False)
    if filtros["q"]:
        qs = qs.filter(
            Q(modelo__nombre__icontains=filtros["q"])
            | Q(color__nombre__icontains=filtros["q"])
            | Q(seccion__nombre__icontains=filtros["q"])
        )

    precio_de = _mapa_precios(generacion)
    especiales = set(
        PrecioEspecial.objects.filter(generacion=generacion).values_list("producto_id", flat=True)
    ) if generacion else set()
    usados = set(Producto.objects.filter(items_pedido__isnull=False).values_list("id", flat=True))
    filas = [
        {"p": p, "precio": precio_de(p), "especial": p.id in especiales, "usado": p.id in usados}
        for p in qs
    ]
    return render(request, "catalogo/productos.html", _contexto(
        request, "productos", generacion,
        filas=filas,
        filtros=filtros,
        secciones=Seccion.objects.all(),
        tamanos=Tamano.objects.all(),
    ))


@staff_required
def producto_alta(request):
    generacion = _generacion(request)
    form = AltaProductosForm(request.POST or None, initial={"seccion": request.GET.get("seccion")})
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        with transaction.atomic():
            modelo = datos.get("modelo")
            if modelo is None:
                modelo = Modelo.objects.create(nombre=datos["modelo_nuevo"])
            creados = existentes = 0
            combinaciones = itertools.product(
                datos["tamanos"], list(datos["colores"]) or [None], list(datos["variantes"]) or [None]
            )
            for tamano, color, variante in combinaciones:
                _, creado = Producto.objects.get_or_create(
                    seccion=datos["seccion"], modelo=modelo, tamano=tamano, color=color, variante=variante,
                    defaults={"activo": True},
                )
                creados += creado
                existentes += not creado
        texto = f"Se crearon {creados} producto(s) de {modelo} en {datos['seccion']}."
        if existentes:
            texto += f" {existentes} ya existían."
        messages.success(request, texto)
        return redirect(_url("catalogo:productos", generacion, seccion=datos["seccion"].pk))
    return render(request, "catalogo/producto_alta.html", _contexto(request, "productos", generacion, form=form))


# ---------------------------------------------------------------------------
# Anillos
# ---------------------------------------------------------------------------

@staff_required
def anillos(request):
    generacion = _generacion(request)
    if generacion is None:
        messages.warning(request, "Primero crea una generación.")
        return redirect("generacion_create")

    if request.method == "POST":
        if request.POST.get("accion") == "eliminar":
            anillo = get_object_or_404(Anillo, pk=request.POST.get("anillo"))
            try:
                with transaction.atomic():
                    anillo.precios.all().delete()
                    anillo.delete()
                messages.success(request, f"Anillo {anillo} eliminado.")
            except ProtectedError:
                messages.error(request, f"El anillo {anillo} ya se usó en pedidos: desactívalo en lugar de eliminarlo.")
            return redirect(_url("catalogo:anillos", generacion))

        errores, cambios = [], 0
        with transaction.atomic():
            vistos = set()
            for anillo in Anillo.objects.all():
                modelo = (request.POST.get(f"modelo-{anillo.id}") or "").strip()
                metal = (request.POST.get(f"metal-{anillo.id}") or "").strip()
                if not modelo or not metal:
                    errores.append(f"El anillo {anillo} necesita modelo y metal.")
                    continue
                clave = (modelo.upper(), metal.upper())
                if clave in vistos:
                    errores.append(f"Anillo repetido: {modelo} - {metal}.")
                    continue
                vistos.add(clave)
                activo = bool(request.POST.get(f"activo-{anillo.id}"))
                if (anillo.modelo, anillo.metal, anillo.activo) != (modelo, metal, activo):
                    anillo.modelo, anillo.metal, anillo.activo = modelo, metal, activo
                    anillo.save()
                    cambios += 1
                try:
                    precio = _decimal(request.POST.get(f"precio-{anillo.id}"))
                except ValueError:
                    errores.append(f"Precio inválido para {anillo}.")
                    continue
                actual = PrecioAnilloGeneracion.objects.filter(anillo=anillo, generacion=generacion).first()
                if precio is None and actual:
                    actual.delete()
                    cambios += 1
                elif precio is not None and (actual is None or actual.precio != precio):
                    PrecioAnilloGeneracion.objects.update_or_create(
                        anillo=anillo, generacion=generacion, defaults={"precio": precio}
                    )
                    cambios += 1

            nuevo_modelo = (request.POST.get("nuevo_modelo") or "").strip()
            nuevo_metal = (request.POST.get("nuevo_metal") or "").strip()
            nuevo_precio = request.POST.get("nuevo_precio")
            if nuevo_modelo or nuevo_metal or (nuevo_precio or "").strip():
                try:
                    precio = _decimal(nuevo_precio)
                except ValueError:
                    precio = None
                    errores.append("El precio del anillo nuevo no es válido.")
                if not nuevo_modelo or not nuevo_metal:
                    errores.append("El anillo nuevo necesita modelo y metal.")
                elif Anillo.objects.filter(modelo__iexact=nuevo_modelo, metal__iexact=nuevo_metal).exists():
                    errores.append(f"Ya existe el anillo {nuevo_modelo} - {nuevo_metal}.")
                elif not errores:
                    anillo = Anillo.objects.create(modelo=nuevo_modelo, metal=nuevo_metal)
                    if precio is not None:
                        PrecioAnilloGeneracion.objects.create(anillo=anillo, generacion=generacion, precio=precio)
                    cambios += 1

            if errores:
                transaction.set_rollback(True)

        if errores:
            for e in errores:
                messages.error(request, e)
            messages.error(request, "No se guardó ningún cambio de anillos.")
        elif cambios:
            messages.success(request, f"Se guardaron {cambios} cambio(s) de anillos.")
        else:
            messages.info(request, "No hubo cambios.")
        return redirect(_url("catalogo:anillos", generacion))

    precios_gen = dict(
        PrecioAnilloGeneracion.objects.filter(generacion=generacion).values_list("anillo_id", "precio")
    )
    usados = set(Anillo.objects.filter(items_pedido_anillo__isnull=False).values_list("id", flat=True))
    filas = [
        {"a": a, "precio": f"{precios_gen[a.id]:.2f}" if a.id in precios_gen else "", "usado": a.id in usados}
        for a in Anillo.objects.all()
    ]
    return render(request, "catalogo/anillos.html", _contexto(request, "anillos", generacion, filas=filas))


# ---------------------------------------------------------------------------
# Dimensiones: secciones, tamaños, modelos, colores, variantes, placas
# ---------------------------------------------------------------------------

@staff_required
def dimensiones(request, tipo="secciones"):
    if tipo not in DIMENSIONES:
        raise Http404
    modelo, form_class, titulo, descripcion = DIMENSIONES[tipo]
    FormSet = modelformset_factory(modelo, form=form_class, extra=1)
    formset = FormSet(request.POST or None, queryset=modelo.objects.all(), prefix=tipo)
    if request.method == "POST" and formset.is_valid():
        guardados = formset.save()
        if guardados:
            messages.success(request, f"{titulo}: se guardaron {len(guardados)} cambio(s).")
        else:
            messages.info(request, "No hubo cambios.")
        return redirect("catalogo:dimensiones", tipo=tipo)
    return render(request, "catalogo/dimensiones.html", _contexto(
        request, "dimensiones", _generacion(request),
        formset=formset,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        tipos=[(k, v[2]) for k, v in DIMENSIONES.items()],
    ))


# ---------------------------------------------------------------------------
# Copiar precios entre generaciones
# ---------------------------------------------------------------------------

def _ajustar(precio, aumento, redondeo):
    nuevo = precio * (Decimal("1") + aumento / Decimal("100"))
    if redondeo:
        paso = Decimal(redondeo)
        nuevo = (nuevo / paso).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * paso
        if nuevo <= 0:
            nuevo = paso
    return nuevo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _plan_copia(datos):
    """Lista de (tipo, descripción, precio_origen, precio_nuevo, existe_en_destino, objeto_origen)."""
    origen, destino = datos["origen"], datos.get("destino")
    aumento, redondeo = datos["aumento"], int(datos["redondeo"])
    plan = []

    def existentes(qs, *campos):
        return set(qs.values_list(*campos)) if destino else set()

    dest_base = existentes(PrecioBase.objects.filter(generacion=destino), "seccion_id", "tamano_id", "variante_id")
    for pb in PrecioBase.objects.filter(generacion=origen).select_related("seccion", "tamano", "variante"):
        desc = f"{pb.seccion} {pb.tamano}" + (f" {pb.variante}" if pb.variante_id else "")
        plan.append(("base", desc, pb.precio, _ajustar(pb.precio, aumento, redondeo),
                     (pb.seccion_id, pb.tamano_id, pb.variante_id) in dest_base, pb))

    dest_esp = existentes(PrecioEspecial.objects.filter(generacion=destino), "producto_id")
    for pe in PrecioEspecial.objects.filter(generacion=origen).select_related(
        "producto__seccion", "producto__modelo", "producto__tamano", "producto__color", "producto__variante"
    ):
        plan.append(("especial", str(pe.producto), pe.precio, _ajustar(pe.precio, aumento, redondeo),
                     (pe.producto_id,) in dest_esp, pe))

    dest_an = existentes(PrecioAnilloGeneracion.objects.filter(generacion=destino), "anillo_id")
    for pa in PrecioAnilloGeneracion.objects.filter(generacion=origen).select_related("anillo"):
        plan.append(("anillo", f"Anillo {pa.anillo}", pa.precio, _ajustar(pa.precio, aumento, redondeo),
                     (pa.anillo_id,) in dest_an, pa))
    return plan


@staff_required
def copiar_precios(request):
    generacion = _generacion(request)
    form = CopiarPreciosForm(request.POST or None, initial={"origen": generacion})
    plan = None
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        plan = _plan_copia(datos)
        sobrescribir = datos["sobrescribir"]
        if request.POST.get("confirmar"):
            with transaction.atomic():
                destino = datos.get("destino")
                if destino is None:
                    destino, _ = Generacion.objects.get_or_create(
                        anio=datos["destino_anio"],
                        defaults={"nombre_generacion": f"Generación {datos['destino_anio']}"},
                    )
                copiados = 0
                for tipo, _, _, nuevo, existe, obj in plan:
                    if existe and not sobrescribir:
                        continue
                    if tipo == "base":
                        PrecioBase.objects.update_or_create(
                            generacion=destino, seccion_id=obj.seccion_id, tamano_id=obj.tamano_id,
                            variante_id=obj.variante_id, defaults={"precio": nuevo},
                        )
                    elif tipo == "especial":
                        PrecioEspecial.objects.update_or_create(
                            generacion=destino, producto_id=obj.producto_id, defaults={"precio": nuevo}
                        )
                    else:
                        PrecioAnilloGeneracion.objects.update_or_create(
                            generacion=destino, anillo_id=obj.anillo_id, defaults={"precio": nuevo}
                        )
                    copiados += 1
            messages.success(
                request, f"Se copiaron {copiados} precio(s) de {datos['origen'].anio} a {destino.anio}."
            )
            return redirect(_url("catalogo:precios", destino))

    resumen = None
    if plan is not None:
        omitidos = sum(1 for p in plan if p[4] and not form.cleaned_data["sobrescribir"])
        resumen = {
            "total": len(plan),
            "a_copiar": len(plan) - omitidos,
            "omitidos": omitidos,
            "filas": [
                {"tipo": t, "desc": d, "antes": a, "despues": n,
                 "omitido": e and not form.cleaned_data["sobrescribir"], "sobrescribe": e}
                for t, d, a, n, e, _ in plan
            ],
        }
    return render(request, "catalogo/copiar_precios.html", _contexto(
        request, "herramientas", generacion, form=form, resumen=resumen,
    ))


# ---------------------------------------------------------------------------
# Subir el Excel
# ---------------------------------------------------------------------------

_SESION_IMPORT = "catalogo_import"


def _dir_importaciones():
    ruta = os.path.join(tempfile.gettempdir(), "seriart_importaciones")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _borrar_pendiente(request):
    pendiente = request.session.pop(_SESION_IMPORT, None)
    if pendiente:
        try:
            os.remove(pendiente["ruta"])
        except OSError:
            pass


@staff_required
def importar(request):
    generacion = _generacion(request)
    form = ImportarExcelForm()
    previa, errores = None, []

    if request.method == "POST" and request.POST.get("accion") == "confirmar":
        pendiente = request.session.get(_SESION_IMPORT)
        if not pendiente or not os.path.exists(pendiente["ruta"]):
            messages.error(request, "La vista previa expiró; vuelve a subir el archivo.")
            return redirect("catalogo:importar")
        try:
            anio, resumen, avisos = importar_catalogo(pendiente["ruta"], anio=pendiente["anio"])
        except ImportacionError as exc:
            messages.error(request, str(exc))
            _borrar_pendiente(request)
            return redirect("catalogo:importar")
        _borrar_pendiente(request)
        for aviso in avisos:
            messages.warning(request, aviso)
        messages.success(
            request,
            f"Catálogo importado para {anio}: {resumen['Productos nuevos']} producto(s) nuevo(s), "
            f"{resumen[f'Precios base ({anio})']} precio(s) base.",
        )
        return redirect(_url("catalogo:precios", Generacion.objects.get(anio=anio)))

    if request.method == "POST" and request.POST.get("accion") == "cancelar":
        _borrar_pendiente(request)
        return redirect("catalogo:importar")

    if request.method == "POST":
        form = ImportarExcelForm(request.POST, request.FILES)
        if form.is_valid():
            _borrar_pendiente(request)
            ruta = os.path.join(_dir_importaciones(), f"{uuid.uuid4().hex}.xlsx")
            with open(ruta, "wb") as destino:
                for trozo in form.cleaned_data["archivo"].chunks():
                    destino.write(trozo)
            try:
                anio, resumen, avisos = importar_catalogo(ruta, anio=form.cleaned_data["anio"], dry_run=True)
            except ImportacionError as exc:
                os.remove(ruta)
                errores = [str(exc)] + exc.errores
            else:
                request.session[_SESION_IMPORT] = {"ruta": ruta, "anio": anio}
                previa = {
                    "anio": anio,
                    "archivo": form.cleaned_data["archivo"].name,
                    "resumen": resumen,
                    "avisos": avisos,
                    "generacion_existe": Generacion.objects.filter(anio=anio).exists(),
                }

    return render(request, "catalogo/importar.html", _contexto(
        request, "herramientas", generacion, form=form, previa=previa, errores=errores,
    ))
