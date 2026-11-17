"""
Importa el catálogo desde el Excel (hoja "TABLA UNICA").

Columnas esperadas, en este orden:
    SECCION | MODELO | COLOR | TAMAÑO | VARIANTE | PRECIO <año> | PLACA (opcional)

PLACA: SI / NO por sección. Vacío = no cambia la sección (si es nueva, queda sin placa).

Uso:
    python manage.py importar_catalogo catalogo_seriart.xlsx
    python manage.py importar_catalogo catalogo_seriart.xlsx --generacion 2027 --dry-run

- Es idempotente: se puede correr varias veces; actualiza precios y no duplica.
- "N/A" o vacío en COLOR / VARIANTE = sin color / sin variante.
- Precios: si todos los productos de una Sección + Tamaño (+ Variante) cuestan
  lo mismo, se guarda un solo PrecioBase. Si algún modelo cuesta distinto, se
  guarda el precio más común como base y el resto como PrecioEspecial.
"""
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogo.models import (
    Color,
    Modelo,
    PrecioBase,
    PrecioEspecial,
    Producto,
    Seccion,
    Tamano,
    Variante,
)
from apps.escuelas.models import Generacion

VACIOS = {"", "N/A", "NA", "-", "NONE"}
ORDEN_TAMANOS = ["CARTA", "DOBLE ESPACIO", "PANORAMICA", "AMPLIADA"]


def limpiar(valor):
    if valor is None:
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip().upper()
    return None if texto in VACIOS else texto


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Importa secciones, modelos, colores, tamaños, variantes, productos y precios desde el Excel."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta al .xlsx")
        parser.add_argument("--hoja", default="TABLA UNICA")
        parser.add_argument(
            "--generacion",
            type=int,
            help="Año de la generación. Si se omite, se lee del encabezado 'PRECIO <año>'.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Muestra el resultado sin guardar nada.")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:
            raise CommandError("Falta openpyxl: pip install openpyxl") from exc

        try:
            libro = openpyxl.load_workbook(opts["archivo"], read_only=True, data_only=True)
        except FileNotFoundError as exc:
            raise CommandError(f"No existe el archivo {opts['archivo']}") from exc
        if opts["hoja"] not in libro.sheetnames:
            raise CommandError(f"No existe la hoja '{opts['hoja']}'. Hojas: {libro.sheetnames}")

        filas = list(libro[opts["hoja"]].iter_rows(values_only=True))
        if not filas:
            raise CommandError("La hoja está vacía.")
        encabezado, filas = filas[0], filas[1:]
        if len(encabezado) < 6:
            raise CommandError("Se esperaban 6 columnas: SECCION, MODELO, COLOR, TAMAÑO, VARIANTE, PRECIO.")

        anio = opts["generacion"]
        if anio is None:
            m = re.search(r"(\d{4})", str(encabezado[5] or ""))
            if not m:
                raise CommandError("No encontré el año en el encabezado de precio; usa --generacion.")
            anio = int(m.group(1))

        registros, errores = self._leer(filas)
        placas, errores_placa = self._placas_por_seccion(filas)
        errores += errores_placa
        if errores:
            for e in errores:
                self.stderr.write(self.style.ERROR(e))
            raise CommandError(f"{len(errores)} fila(s) con errores; no se importó nada.")

        try:
            with transaction.atomic():
                resumen = self._importar(registros, anio)
                resumen.update(self._aplicar_placas(placas))
                if opts["dry_run"]:
                    raise DryRun
        except DryRun:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardó nada."))

        for clave, valor in resumen.items():
            self.stdout.write(f"  {clave}: {valor}")
        self.stdout.write(self.style.SUCCESS(f"Catálogo importado para la generación {anio}."))

    # ------------------------------------------------------------------

    def _leer(self, filas):
        registros, errores = [], []
        vistos = set()
        for n, fila in enumerate(filas, start=2):
            if not fila or all(c is None for c in fila[:6]):
                continue
            seccion, modelo, color, tamano, variante = (limpiar(c) for c in fila[:5])
            precio_raw = fila[5]
            if not (seccion and modelo and tamano):
                errores.append(f"Fila {n}: faltan SECCION, MODELO o TAMAÑO.")
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
            registros.append(dict(seccion=seccion, modelo=modelo, color=color,
                                  tamano=tamano, variante=variante, precio=precio))
        return registros, errores

    def _placas_por_seccion(self, filas):
        """Lee la columna PLACA (7ª). Devuelve {seccion: True/False} y errores."""
        valores, errores = {}, []
        for n, fila in enumerate(filas, start=2):
            if len(fila) < 7 or not limpiar(fila[0]):
                continue
            seccion, crudo = limpiar(fila[0]), limpiar(fila[6])
            if crudo is None:
                continue
            if crudo not in ("SI", "SÍ", "NO"):
                errores.append(f"Fila {n}: PLACA debe ser SI o NO ({fila[6]!r}).")
                continue
            valor = crudo != "NO"
            if valores.setdefault(seccion, valor) != valor:
                errores.append(f"Fila {n}: la sección {seccion} tiene PLACA SI y NO en distintas filas.")
        return valores, errores

    def _aplicar_placas(self, placas):
        cambios = 0
        for seccion in Seccion.objects.all():
            if seccion.nombre in placas:
                if seccion.lleva_placa != placas[seccion.nombre]:
                    seccion.lleva_placa = placas[seccion.nombre]
                    seccion.save(update_fields=["lleva_placa"])
                    cambios += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f"  Aviso: la sección {seccion.nombre} no tiene valor en PLACA; "
                    f"se queda en {'SI' if seccion.lleva_placa else 'NO'}."
                ))
        con_placa = Seccion.objects.filter(lleva_placa=True).values_list("nombre", flat=True)
        return {
            "Secciones con placa": ", ".join(con_placa) or "ninguna",
            "Secciones con placa actualizadas": cambios,
        }

    def _importar(self, registros, anio):
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
        for (s, t), items in por_seccion_tamano.items():
            if len({p for _, p in items}) == 1:
                subgrupos = {None: items}
            else:
                subgrupos = defaultdict(list)
                for producto, precio in items:
                    subgrupos[producto.variante].append((producto, precio))

            for variante, sub in subgrupos.items():
                comun = Counter(p for _, p in sub).most_common(1)[0][0]
                PrecioBase.objects.update_or_create(
                    generacion=generacion, seccion=s, tamano=t, variante=variante,
                    defaults={"precio": comun},
                )
                bases += 1
                for producto, precio in sub:
                    if precio != comun:
                        PrecioEspecial.objects.update_or_create(
                            generacion=generacion, producto=producto, defaults={"precio": precio}
                        )
                        especiales += 1
                    else:
                        PrecioEspecial.objects.filter(generacion=generacion, producto=producto).delete()

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
        }
