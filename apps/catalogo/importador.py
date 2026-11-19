"""
Importación del catálogo desde el Excel (hoja "TABLA UNICA").

Lo usan el comando `importar_catalogo` y el panel de catálogo.

Columnas (se buscan por nombre en el encabezado, en cualquier orden):
    CONCEPTO (opcional) | SECCION | MODELO | COLOR | TAMAÑO | VARIANTE | PRECIO <año> | PLACA (opcional)

- Idempotente: se puede correr varias veces; actualiza precios y no duplica.
- "N/A" o vacío en COLOR / VARIANTE = sin color / sin variante.
- "N/A" o vacío en TAMAÑO = tamaño ÚNICO (secciones como CORREDIZA o LIBRO).
- CONCEPTO: DIPLOMA/AGRADECIMIENTO o FOTO PANORAMICA. Se guarda en el tamaño y
  decide cómo se ofrece en la captura. Un tamaño no puede tener dos conceptos.
- PLACA: SI / NO por sección. Vacío = no cambia la sección (si es nueva, queda sin placa).
- Precios: si todos los productos de una Sección + Tamaño (+ Variante) cuestan
  lo mismo, se guarda un solo PrecioBase. Si algún modelo cuesta distinto, se
  guarda el precio más común como base y el resto como PrecioEspecial.
"""
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.escuelas.models import Generacion

from .models import Color, Modelo, PrecioBase, PrecioEspecial, Producto, Seccion, Tamano, Variante

HOJA = "TABLA UNICA"
VACIOS = {"", "N/A", "NA", "-", "NONE"}
TAMANO_UNICO = "ÚNICO"  # productos sin tamaño en el Excel
ORDEN_TAMANOS = ["CARTA", "DOBLE ESPACIO", "ESTANDAR", "AMPLIADA", TAMANO_UNICO]
# Nombres viejos de tamaño en el Excel -> nombre actual
TAMANOS_ALIAS = {"PANORAMICA": "ESTANDAR"}
# Columna CONCEPTO del Excel -> Tamano.concepto
CONCEPTOS = {
    "DIPLOMA/AGRADECIMIENTO": Tamano.CONCEPTO_DIPLOMA,
    "DIPLOMA / AGRADECIMIENTO": Tamano.CONCEPTO_DIPLOMA,
    "DIPLOMA": Tamano.CONCEPTO_DIPLOMA,
    "AGRADECIMIENTO": Tamano.CONCEPTO_DIPLOMA,
    "FOTO PANORAMICA": Tamano.CONCEPTO_PANORAMICA,
    "FOTO PANORÁMICA": Tamano.CONCEPTO_PANORAMICA,
    "PANORAMICA": Tamano.CONCEPTO_PANORAMICA,
}
COLUMNAS = ["CONCEPTO", "SECCION", "MODELO", "COLOR", "TAMANO", "VARIANTE", "PRECIO", "PLACA"]
OBLIGATORIAS = ["SECCION", "MODELO", "COLOR", "TAMANO", "VARIANTE", "PRECIO"]


class ImportacionError(Exception):
    """El archivo no se puede importar. `errores` trae el detalle por fila."""

    def __init__(self, mensaje, errores=None):
        super().__init__(mensaje)
        self.errores = errores or []


class _DryRun(Exception):
    pass


def limpiar(valor):
    if valor is None:
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip().upper()
    return None if texto in VACIOS else texto


def _columnas(encabezado):
    """{"SECCION": 1, "PRECIO": 6, ...} según los nombres del encabezado."""
    sin_acentos = str.maketrans("ÁÉÍÓÚÑ", "AEIOUN")
    indices = {}
    for i, celda in enumerate(encabezado):
        nombre = (limpiar(celda) or "").translate(sin_acentos)
        for col in COLUMNAS:
            if col not in indices and (nombre == col or (col == "PRECIO" and nombre.startswith("PRECIO"))):
                indices[col] = i
    return indices


def _celda(fila, indices, col):
    i = indices.get(col)
    return fila[i] if i is not None and i < len(fila) else None


def importar_catalogo(archivo, anio=None, hoja=HOJA, dry_run=False):
    """
    Importa el Excel. `archivo` es una ruta o un archivo abierto.
    Devuelve (anio, resumen: dict, avisos: list). Lanza ImportacionError.
    Con dry_run=True todo se calcula dentro de una transacción que se revierte.
    """
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise ImportacionError("Falta openpyxl: pip install openpyxl") from exc

    try:
        libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except FileNotFoundError as exc:
        raise ImportacionError(f"No existe el archivo {archivo}") from exc
    except Exception as exc:
        raise ImportacionError("No se pudo leer el archivo; ¿es un .xlsx válido?") from exc
    if hoja not in libro.sheetnames:
        raise ImportacionError(f"No existe la hoja '{hoja}'. Hojas: {', '.join(libro.sheetnames)}")

    filas = list(libro[hoja].iter_rows(values_only=True))
    if not filas:
        raise ImportacionError("La hoja está vacía.")
    encabezado, filas = filas[0], filas[1:]
    indices = _columnas(encabezado)
    faltan = [c for c in OBLIGATORIAS if c not in indices]
    if faltan:
        raise ImportacionError(
            "Faltan columnas en el encabezado: " + ", ".join("TAMAÑO" if c == "TAMANO" else c for c in faltan)
            + ". Se esperan SECCION, MODELO, COLOR, TAMAÑO, VARIANTE y PRECIO <año> (CONCEPTO y PLACA opcionales)."
        )

    if anio is None:
        m = re.search(r"(\d{4})", str(encabezado[indices["PRECIO"]] or ""))
        if not m:
            raise ImportacionError("No encontré el año en el encabezado de precio (ej. 'PRECIO 2027').")
        anio = int(m.group(1))

    registros, errores = _leer(filas, indices)
    placas, errores_placa = _placas_por_seccion(filas, indices)
    conceptos, errores_concepto = _conceptos_por_tamano(registros)
    errores += errores_placa + errores_concepto
    if errores:
        raise ImportacionError(f"{len(errores)} fila(s) con errores; no se importó nada.", errores)

    avisos = []
    try:
        with transaction.atomic():
            resumen = _importar(registros, anio)
            resumen.update(_aplicar_placas(placas, avisos))
            resumen.update(_aplicar_conceptos(conceptos))
            if dry_run:
                raise _DryRun
    except _DryRun:
        pass
    return anio, resumen, avisos


def _leer(filas, indices):
    registros, errores = [], []
    vistos = set()
    for n, fila in enumerate(filas, start=2):
        if not fila or all(_celda(fila, indices, c) is None for c in OBLIGATORIAS):
            continue
        seccion, modelo, color, tamano, variante = (
            limpiar(_celda(fila, indices, c)) for c in ("SECCION", "MODELO", "COLOR", "TAMANO", "VARIANTE")
        )
        tamano = TAMANOS_ALIAS.get(tamano, tamano) or TAMANO_UNICO
        precio_raw = _celda(fila, indices, "PRECIO")
        concepto_raw = limpiar(_celda(fila, indices, "CONCEPTO"))
        if not (seccion and modelo):
            errores.append(f"Fila {n}: faltan SECCION o MODELO.")
            continue
        concepto = None
        if concepto_raw:
            concepto = CONCEPTOS.get(concepto_raw)
            if concepto is None:
                errores.append(
                    f"Fila {n}: CONCEPTO debe ser DIPLOMA/AGRADECIMIENTO o FOTO PANORAMICA ({concepto_raw!r})."
                )
                continue
        try:
            precio = Decimal(str(precio_raw)).quantize(Decimal("0.01"))
            if precio <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            errores.append(f"Fila {n}: precio inválido ({precio_raw!r}).")
            continue
        clave = (seccion, modelo, color, tamano, variante)
        if clave in vistos:
            errores.append(f"Fila {n}: producto repetido {clave}.")
            continue
        vistos.add(clave)
        registros.append(dict(seccion=seccion, modelo=modelo, color=color, tamano=tamano,
                              variante=variante, precio=precio, concepto=concepto, fila=n))
    return registros, errores


def _conceptos_por_tamano(registros):
    """{tamaño: concepto} desde la columna CONCEPTO; error si un tamaño tiene dos."""
    valores, errores = {}, []
    for r in registros:
        if r["concepto"] is None:
            continue
        previo = valores.setdefault(r["tamano"], r["concepto"])
        if previo != r["concepto"]:
            errores.append(
                f"Fila {r['fila']}: el tamaño {r['tamano']} aparece con dos conceptos distintos."
            )
    return valores, errores


def _aplicar_conceptos(conceptos):
    cambios = 0
    for tamano in Tamano.objects.filter(nombre__in=conceptos):
        if tamano.concepto != conceptos[tamano.nombre]:
            tamano.concepto = conceptos[tamano.nombre]
            tamano.save(update_fields=["concepto"])
            cambios += 1
    etiquetas = dict(Tamano.CONCEPTO_CHOICES)
    return {
        "Concepto por tamaño": ", ".join(
            f"{t.nombre}: {etiquetas.get(t.concepto) or 'sin definir'}" for t in Tamano.objects.all()
        ),
        "Tamaños con concepto actualizado": cambios,
    }


def _placas_por_seccion(filas, indices):
    """Lee la columna PLACA. Devuelve {seccion: True/False} y errores."""
    valores, errores = {}, []
    if "PLACA" not in indices:
        return valores, errores
    for n, fila in enumerate(filas, start=2):
        seccion = limpiar(_celda(fila, indices, "SECCION")) if fila else None
        if not seccion:
            continue
        crudo = limpiar(_celda(fila, indices, "PLACA"))
        if crudo is None:
            continue
        if crudo not in ("SI", "SÍ", "NO"):
            errores.append(f"Fila {n}: PLACA debe ser SI o NO ({_celda(fila, indices, 'PLACA')!r}).")
            continue
        valor = crudo != "NO"
        if valores.setdefault(seccion, valor) != valor:
            errores.append(f"Fila {n}: la sección {seccion} tiene PLACA SI y NO en distintas filas.")
    return valores, errores


def _aplicar_placas(placas, avisos):
    cambios = 0
    for seccion in Seccion.objects.all():
        if seccion.nombre in placas:
            if seccion.lleva_placa != placas[seccion.nombre]:
                seccion.lleva_placa = placas[seccion.nombre]
                seccion.save(update_fields=["lleva_placa"])
                cambios += 1
        else:
            avisos.append(
                f"La sección {seccion.nombre} no tiene valor en PLACA; "
                f"se queda en {'SI' if seccion.lleva_placa else 'NO'}."
            )
    con_placa = Seccion.objects.filter(lleva_placa=True).values_list("nombre", flat=True)
    return {
        "Secciones con placa": ", ".join(con_placa) or "ninguna",
        "Secciones con placa actualizadas": cambios,
    }


def _importar(registros, anio):
    generacion, _ = Generacion.objects.get_or_create(
        anio=anio, defaults={"nombre_generacion": f"Generación {anio}"}
    )
    cache = {Seccion: {}, Modelo: {}, Color: {}, Tamano: {}, Variante: {}}

    def obtener(model, nombre, **defaults):
        if nombre is None:
            return None
        if nombre not in cache[model]:
            cache[model][nombre], _ = model.objects.get_or_create(nombre=nombre, defaults=defaults)
        return cache[model][nombre]

    productos_nuevos = 0
    grupos = defaultdict(list)  # (seccion, tamano, variante) -> [(producto, precio)]
    for r in registros:
        orden_t = ORDEN_TAMANOS.index(r["tamano"]) + 1 if r["tamano"] in ORDEN_TAMANOS else 99
        producto, creado = Producto.objects.get_or_create(
            seccion=obtener(Seccion, r["seccion"]),
            modelo=obtener(Modelo, r["modelo"]),
            tamano=obtener(Tamano, r["tamano"], orden=orden_t),
            color=obtener(Color, r["color"]),
            variante=obtener(Variante, r["variante"]),
        )
        productos_nuevos += creado
        grupos[(producto.seccion, producto.tamano, producto.variante)].append((producto, r["precio"]))

    # Si dentro de Sección+Tamaño todas las variantes cuestan igual, se guarda sin variante.
    por_seccion_tamano = defaultdict(list)
    for (s, t, v), items in grupos.items():
        por_seccion_tamano[(s, t)].extend(items)

    bases, especiales = 0, 0
    bases_ids, productos_ids = set(), set()
    for (s, t), items in por_seccion_tamano.items():
        if len({p for _, p in items}) == 1:
            subgrupos = {None: items}
        else:
            subgrupos = defaultdict(list)
            for producto, precio in items:
                subgrupos[producto.variante].append((producto, precio))

        for variante, sub in subgrupos.items():
            comun = Counter(p for _, p in sub).most_common(1)[0][0]
            base, _ = PrecioBase.objects.update_or_create(
                generacion=generacion, seccion=s, tamano=t, variante=variante,
                defaults={"precio": comun},
            )
            bases += 1
            bases_ids.add(base.pk)
            for producto, precio in sub:
                productos_ids.add(producto.pk)
                if precio != comun:
                    PrecioEspecial.objects.update_or_create(
                        generacion=generacion, producto=producto, defaults={"precio": precio}
                    )
                    especiales += 1
                else:
                    PrecioEspecial.objects.filter(generacion=generacion, producto=producto).delete()

    # El Excel es la lista completa del año: los precios de esa generación que ya no
    # vienen en él se quitan (los productos se quedan, pero sin precio no se ofrecen;
    # los pedidos guardan su propio precio y no cambian).
    quitados = PrecioBase.objects.filter(generacion=generacion).exclude(pk__in=bases_ids).delete()[0]
    quitados += (
        PrecioEspecial.objects.filter(generacion=generacion).exclude(producto_id__in=productos_ids).delete()[0]
    )

    return {
        "Filas leídas": len(registros),
        "Productos nuevos": productos_nuevos,
        "Productos totales": Producto.objects.count(),
        "Secciones": Seccion.objects.count(),
        "Modelos": Modelo.objects.count(),
        "Colores": Color.objects.count(),
        "Tamaños": Tamano.objects.count(),
        "Variantes": Variante.objects.count(),
        f"Precios base ({anio})": bases,
        f"Precios especiales ({anio})": especiales,
        f"Precios quitados ({anio}, ya no están en el Excel)": quitados,
    }
