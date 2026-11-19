"""
Copia los datos de la versión 1 (base vieja) a la base nueva de la v2.

Requisitos:
  - La base nueva ya migrada (`manage.py migrate`) y SIN escuelas, alumnos ni pedidos.
  - El catálogo de 2027 ya importado desde el Excel (`importar_catalogo`), para que los
    nombres de secciones/modelos/tamaños coincidan con los del Excel.
  - La conexión a la base vieja en settings (DB_V1_NAME=...).

Qué hace:
  - Usuarios (con sus contraseñas), generaciones, escuelas, grupos y alumnos: mismos IDs.
  - Catálogo de cada generación vieja (ej. 2026): cada modelo viejo se convierte a producto
    nuevo y sus precios se agrupan por sección + tamaño (como el importador del Excel).
      * "PIRAMIDAL NEGRO" -> modelo PIRAMIDAL, color NEGRO (CAOVA -> CAOBA), salvo que el
        nombre completo ya exista como modelo en esa sección (ej. MONACO NEGRO, LIBRO VINO).
      * Tamaños DIPLOMA y AGRADECIMIENTO -> CARTA (el concepto del artículo dice cuál es).
  - Anillos y sus precios.
  - Pedidos con sus artículos (conservando el precio cobrado), extras, observaciones,
    pagos y descuentos. El estado se recalcula: pendiente/proceso según lo pagado.
  - Verifica conteos y que el total de cada pedido cuadre.

Uso:
  python manage.py migrar_desde_v1 --generaciones   # 1) antes de importar_catalogo
  python manage.py importar_catalogo catalogo.xlsx  # 2)
  python manage.py migrar_desde_v1 --dry-run   # todo en una transacción que se revierte
  python manage.py migrar_desde_v1
"""
from collections import Counter, defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.alumnos.models import Alumno
from apps.catalogo import importador
from apps.catalogo.models import (
    Anillo, Color, Modelo, Placa, PrecioAnilloGeneracion, Producto, Seccion, Tamano,
)
from apps.escuelas.models import Escuela, Generacion, Grupo
from apps.ventas.models import (
    Observacion,
    Pago,
    Pedido,
    PedidoDescuento,
    PedidoEstadoHistorial,
    PedidoItemAnillo,
    PedidoItemBase,
    PedidoItemExtra,
)

COLORES = {"NEGRO": "NEGRO", "VINO": "VINO", "MIEL": "MIEL", "CAOBA": "CAOBA", "CAOVA": "CAOBA"}
TAMANOS = {"DIPLOMA": "CARTA", "AGRADECIMIENTO": "CARTA", "PANORAMICA": "ESTANDAR"}
CONCEPTOS = {
    "PANORAMICA": PedidoItemBase.CONCEPTO_PANORAMICA,
    "DIPLOMA": PedidoItemBase.CONCEPTO_DIPLOMA,
    "AGRADECIMIENTO": PedidoItemBase.CONCEPTO_AGRADECIMIENTO,
}
PLACAS = {
    "arena": "Arena", "mediterranea": "Mediterránea", "4_piezas": "4 piezas", "extendida": "Extendida",
    "corte_plano": "Corte plano", "palermo": "Palermo", "circulo": "Círculo", "corazon": "Corazón",
    "estrella": "Estrella", "columnas": "Columnas", "pergamino": "Pergamino",
}


class _DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Copia los datos de la base de la versión 1 a la base de la v2."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Hace todo y al final lo revierte.")
        parser.add_argument(
            "--generaciones", action="store_true",
            help="Solo copia las generaciones de v1 con sus IDs. Córrelo ANTES de importar_catalogo "
                 "para que la generación del Excel no ocupe un ID de la v1.",
        )

    # ------------------------------------------------------------------
    def _solo_generaciones(self):
        self.v1 = connections["v1"].cursor()
        gens = self._filas("escuelas_generacion")
        ya = {g.anio: g.id for g in Generacion.objects.all()}
        ocupados = set(Generacion.objects.values_list("id", flat=True))
        with transaction.atomic():
            for g in gens:
                if g["anio"] in ya:
                    if ya[g["anio"]] != g["id"]:
                        raise CommandError(f"La generación {g['anio']} ya existe con otro ID.")
                    continue
                if g["id"] in ocupados:
                    raise CommandError(f"El ID {g['id']} ya lo usa otra generación.")
                Generacion.objects.create(id=g["id"], nombre_generacion=g["nombre"], anio=g["anio"])
                self.stdout.write(f"  Generación {g['anio']} (ID {g['id']})")
        # MySQL/Postgres: que los IDs automáticos sigan después de los copiados
        from django.core.management.color import no_style
        from django.db import connection
        with connection.cursor() as c:
            for sql in connection.ops.sequence_reset_sql(no_style(), [Generacion]):
                c.execute(sql)
        self.stdout.write(self.style.SUCCESS("Generaciones de v1 copiadas."))

    def handle(self, *args, **opts):
        if "v1" not in connections.databases:
            raise CommandError("Falta la conexión 'v1': define DB_V1_NAME en el .env.")
        if opts["generaciones"]:
            return self._solo_generaciones()
        if Escuela.objects.exists() or Alumno.objects.exists() or Pedido.objects.exists():
            raise CommandError("La base nueva ya tiene escuelas, alumnos o pedidos: no se migra encima.")
        if not Producto.objects.exists():
            raise CommandError("Primero importa el catálogo del Excel (importar_catalogo).")

        self.v1 = connections["v1"].cursor()
        self.avisos = []
        try:
            with transaction.atomic():
                resumen = self._migrar()
                self._verificar(resumen)
                if opts["dry_run"]:
                    raise _DryRun
        except _DryRun:
            self.stdout.write(self.style.WARNING("DRY RUN: se revirtió todo, no se guardó nada."))

        for clave, valor in resumen.items():
            self.stdout.write(f"  {clave}: {valor}")
        for aviso in self.avisos:
            self.stdout.write(self.style.WARNING(f"  Aviso: {aviso}"))
        if not opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Migración desde v1 terminada."))

    # ------------------------------------------------------------------
    def _filas(self, tabla, orden="id"):
        self.v1.execute(f"SELECT * FROM `{tabla}` ORDER BY {orden}")
        columnas = [c[0] for c in self.v1.description]
        return [dict(zip(columnas, fila)) for fila in self.v1.fetchall()]

    def _conservar_fechas(self, modelo, filas, campos):
        """bulk_create pisa auto_now/auto_now_add: se restauran los valores originales."""
        for f in filas:
            valores = {c: f[c] for c in campos if f.get(c) is not None}
            if valores:
                modelo.objects.filter(pk=f["id"]).update(**valores)

    # ------------------------------------------------------------------
    def _migrar(self):
        r = {}
        User = get_user_model()

        # ---------- Usuarios ----------
        usuarios = self._filas("auth_user")
        existentes = set(User.objects.values_list("username", flat=True))
        nuevos = [u for u in usuarios if u["username"] not in existentes]
        if len(nuevos) != len(usuarios):
            self.avisos.append(
                "Usuarios que ya existían en la base nueva y no se copiaron: "
                + ", ".join(u["username"] for u in usuarios if u["username"] in existentes)
            )
        User.objects.bulk_create([User(**u) for u in nuevos])
        r["Usuarios"] = len(nuevos)

        # ---------- Generaciones / escuelas / grupos / alumnos ----------
        gens = self._filas("escuelas_generacion")
        ya = {g.anio: g.id for g in Generacion.objects.all()}
        for g in gens:
            if g["anio"] in ya and ya[g["anio"]] != g["id"]:
                raise CommandError(f"La generación {g['anio']} ya existe con otro ID; no se puede conservar el ID.")
        Generacion.objects.bulk_create(
            [Generacion(id=g["id"], nombre_generacion=g["nombre"], anio=g["anio"]) for g in gens if g["anio"] not in ya]
        )
        r["Generaciones"] = len(gens)

        escuelas = self._filas("escuelas_escuela")
        Escuela.objects.bulk_create([
            Escuela(id=e["id"], nombre_escuela=e["nombre"], direccion=e["direccion"] or "",
                    telefono=e["telefono"] or "", nivel=Escuela.NIVEL_OTRO)
            for e in escuelas
        ])
        rel = self._filas("escuelas_escuela_generaciones")
        Escuela.generaciones.through.objects.bulk_create([
            Escuela.generaciones.through(id=x["id"], escuela_id=x["escuela_id"], generacion_id=x["generacion_id"])
            for x in rel
        ])
        r["Escuelas"] = len(escuelas)

        grupos = self._filas("escuelas_grupo")
        Grupo.objects.bulk_create([
            Grupo(id=g["id"], nombre_grupo=g["nombre"], escuela_id=g["escuela_id"], generacion_id=g["generacion_id"],
                  fecha_fotografia=g["fecha_fotografia"], hora_fotografia=g["hora_fotografia"],
                  lugar_fotografia=g["lugar_fotografia"] or "")
            for g in grupos
        ])
        r["Grupos"] = len(grupos)

        alumnos = self._filas("alumnos_alumno")
        Alumno.objects.bulk_create([
            Alumno(id=a["id"], nombre_alumno=a["nombre"], telefono=a["telefono"] or "",
                   folio_fotos=a["folio_fotos"] or "", grupo_id=a["grupo_id"])
            for a in alumnos
        ])
        r["Alumnos"] = len(alumnos)

        # ---------- Catálogo viejo -> productos y precios por generación ----------
        secciones = {s["id"]: importador.limpiar(s["nombre"]) for s in self._filas("catalogo_seccion")}
        tamanos = {t["id"]: importador.limpiar(t["nombre"]) for t in self._filas("catalogo_tamanoproducto")}
        modelos_v1 = {m["id"]: m for m in self._filas("catalogo_modelo")}
        modelos_por_seccion = defaultdict(set)
        for s_nombre, m_nombre in Producto.objects.values_list("seccion__nombre", "modelo__nombre"):
            modelos_por_seccion[s_nombre].add(m_nombre)

        def convertir(modelo_v1):
            seccion = secciones[modelo_v1["seccion_id"]]
            tamano_v1 = tamanos[modelo_v1["tamano_producto_id"]]
            nombre = importador.limpiar(modelo_v1["nombre"])
            color = None
            partes = nombre.split()
            if nombre not in modelos_por_seccion[seccion] and len(partes) > 1 and partes[-1] in COLORES:
                nombre, color = " ".join(partes[:-1]), COLORES[partes[-1]]
            return dict(seccion=seccion, modelo=nombre, color=color,
                        tamano=TAMANOS.get(tamano_v1, tamano_v1), variante=None), tamano_v1

        productos_antes = set(Producto.objects.values_list("id", flat=True))
        precios_v1 = self._filas("catalogo_preciobasegeneracion")
        anios = {g["id"]: g["anio"] for g in gens}
        por_anio = defaultdict(list)
        for p in precios_v1:
            registro, _ = convertir(modelos_v1[p["modelo_id"]])
            por_anio[anios[p["generacion_id"]]].append({**registro, "precio": Decimal(p["precio"])})
        for anio, registros in sorted(por_anio.items()):
            res = importador._importar(registros, anio)
            r[f"Precios base {anio}"] = res[f"Precios base ({anio})"]
            r[f"Precios especiales {anio}"] = res[f"Precios especiales ({anio})"]

        # Producto nuevo de cada modelo viejo (incluye los que no tienen precio)
        producto_de = {}
        for mid, m in modelos_v1.items():
            reg, _ = convertir(m)
            producto, _ = Producto.objects.get_or_create(
                seccion=Seccion.objects.get_or_create(nombre=reg["seccion"])[0],
                modelo=Modelo.objects.get_or_create(nombre=reg["modelo"])[0],
                tamano=Tamano.objects.get_or_create(nombre=reg["tamano"])[0],
                color=Color.objects.get_or_create(nombre=reg["color"])[0] if reg["color"] else None,
                variante=None,
            )
            producto_de[mid] = producto
        creados = Producto.objects.exclude(id__in=productos_antes).select_related(
            "seccion", "modelo", "tamano", "color")
        r["Productos agregados desde v1"] = creados.count()
        if creados:
            self.avisos.append(
                "Productos que solo existían en el catálogo viejo (revisa en el panel si siguen vigentes): "
                + "; ".join(str(p) for p in creados)
            )

        # ---------- Anillos ----------
        anillos = self._filas("catalogo_anillo")
        Anillo.objects.bulk_create([Anillo(id=a["id"], modelo=a["modelo"], metal=a["metal"]) for a in anillos])
        precios_anillo = self._filas("catalogo_precioanillogeneracion")
        PrecioAnilloGeneracion.objects.bulk_create([
            PrecioAnilloGeneracion(id=p["id"], anillo_id=p["anillo_id"], generacion_id=p["generacion_id"],
                                   precio=p["precio"])
            for p in precios_anillo
        ])
        r["Anillos"] = len(anillos)

        # ---------- Pedidos ----------
        pedidos = self._filas("ventas_pedido")
        Pedido.objects.bulk_create([
            Pedido(id=p["id"], alumno_id=p["alumno_id"], total=p["total"],
                   estado=p["estado"] if p["estado"] in ("listo", "entregado") else Pedido.SIN_ANTICIPO,
                   recibido_por=p["recibido_por"], fecha_entrega=p["fecha_entrega"],
                   notas_entrega=p["notas_entrega"])
            for p in pedidos
        ])
        self._conservar_fechas(Pedido, pedidos, ["fecha", "actualizado"])
        r["Pedidos"] = len(pedidos)

        placas = {p.nombre: p for p in Placa.objects.all()}
        items = self._filas("ventas_pedidoitembase")
        nuevos_items = []
        for i in items:
            m = modelos_v1[i["modelo_id"]]
            _, tamano_v1 = convertir(m)
            placa = None
            if i["placa"]:
                nombre_placa = PLACAS.get(i["placa"], i["placa"])
                placa = placas.get(nombre_placa)
                if placa is None:
                    placa = placas[nombre_placa] = Placa.objects.create(nombre=nombre_placa)
            nuevos_items.append(PedidoItemBase(
                id=i["id"], pedido_id=i["pedido_id"], producto=producto_de[i["modelo_id"]],
                concepto=CONCEPTOS.get(tamano_v1, PedidoItemBase.CONCEPTO_OTRO),
                placa=placa, color_placa=i["color_placa"], cantidad=i["cantidad"],
                precio_unitario=i["precio_unitario"], subtotal=i["subtotal"],
            ))
        PedidoItemBase.objects.bulk_create(nuevos_items)  # sin save(): conserva el precio cobrado
        r["Artículos base"] = len(items)

        aros = self._filas("ventas_pedidoitemanillo")
        PedidoItemAnillo.objects.bulk_create([
            PedidoItemAnillo(id=a["id"], pedido_id=a["pedido_id"], anillo_id=a["anillo_id"],
                             tamano_anillo=a["tamano_anillo"], cantidad=a["cantidad"],
                             precio_unitario=a["precio_unitario"], subtotal=a["subtotal"])
            for a in aros
        ])
        r["Artículos anillo"] = len(aros)

        extras = self._filas("ventas_pedidoitemextra")
        PedidoItemExtra.objects.bulk_create([
            PedidoItemExtra(id=e["id"], pedido_id=e["pedido_id"], nombre=e["nombre"], descripcion=e["descripcion"],
                            cantidad=e["cantidad"], precio_unitario=e["precio_unitario"], subtotal=e["subtotal"])
            for e in extras
        ])
        r["Extras"] = len(extras)

        obs = self._filas("ventas_observacion")
        Observacion.objects.bulk_create([
            Observacion(id=o["id"], pedido_id=o["pedido_id"], texto=o["texto"]) for o in obs
        ])
        self._conservar_fechas(Observacion, obs, ["fecha"])
        r["Observaciones"] = len(obs)

        pagos = self._filas("ventas_pago")
        Pago.objects.bulk_create([
            Pago(id=p["id"], pedido_id=p["pedido_id"], fecha_pago=p["fecha_pago"], monto=p["monto"],
                 folio_nota=p["folio_nota"])
            for p in pagos
        ])
        self._conservar_fechas(Pago, pagos, ["fecha_registro"])
        r["Pagos"] = len(pagos)

        descuentos = self._filas("ventas_pedidodescuento")
        PedidoDescuento.objects.bulk_create([
            PedidoDescuento(id=d["id"], pedido_id=d["pedido_id"], monto=d["monto"], motivo=d["motivo"])
            for d in descuentos
        ])
        self._conservar_fechas(PedidoDescuento, descuentos, ["fecha"])
        r["Descuentos"] = len(descuentos)

        # ---------- Estados por anticipo + historial inicial ----------
        cambios = Counter()
        for pedido in Pedido.objects.all():
            if pedido.estado == Pedido.SIN_ANTICIPO:
                nuevo = pedido.estado_por_anticipo()
                if nuevo != pedido.estado:
                    Pedido.objects.filter(pk=pedido.pk).update(estado=nuevo)
                    pedido.estado = nuevo
            PedidoEstadoHistorial.objects.create(
                pedido=pedido, estado_anterior="", estado_nuevo=pedido.estado,
                nota="Migrado desde la versión 1",
            )
            cambios[pedido.get_estado_display()] += 1
        r["Estados"] = dict(cambios)
        return r

    # ------------------------------------------------------------------
    def _verificar(self, r):
        """Conteos iguales a la v1 y total de cada pedido = artículos - descuentos."""
        tablas = {
            "escuelas_escuela": Escuela, "escuelas_grupo": Grupo, "alumnos_alumno": Alumno,
            "ventas_pedido": Pedido, "ventas_pedidoitembase": PedidoItemBase,
            "ventas_pedidoitemanillo": PedidoItemAnillo, "ventas_pedidoitemextra": PedidoItemExtra,
            "ventas_observacion": Observacion, "ventas_pago": Pago, "ventas_pedidodescuento": PedidoDescuento,
            "catalogo_anillo": Anillo, "catalogo_precioanillogeneracion": PrecioAnilloGeneracion,
        }
        for tabla, modelo in tablas.items():
            self.v1.execute(f"SELECT COUNT(*) FROM `{tabla}`")
            antes = self.v1.fetchone()[0]
            ahora = modelo.objects.count()
            if antes != ahora:
                raise CommandError(f"Conteo distinto en {tabla}: v1={antes}, v2={ahora}. Se revirtió todo.")

        descuadres = []
        for p in Pedido.objects.prefetch_related("items_base", "items_anillo", "items_extra", "descuentos"):
            calculado = (
                sum((i.subtotal for i in p.items_base.all()), Decimal("0"))
                + sum((i.subtotal for i in p.items_anillo.all()), Decimal("0"))
                + sum((i.subtotal for i in p.items_extra.all()), Decimal("0"))
                - sum((d.monto for d in p.descuentos.all()), Decimal("0"))
            )
            if max(calculado, Decimal("0")) != p.total:
                descuadres.append(f"#{p.id} total={p.total} artículos={calculado}")
        if descuadres:
            self.avisos.append("Pedidos cuyo total guardado no cuadra con sus artículos (ya venía así de v1): "
                               + "; ".join(descuadres))
        r["Verificación"] = "conteos iguales" + ("" if not descuadres else f", {len(descuadres)} total(es) a revisar")
