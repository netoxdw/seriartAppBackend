"""
Importa el catálogo desde el Excel (hoja "TABLA UNICA").
La lógica vive en apps/catalogo/importador.py (la usa también el panel).

Uso:
    python manage.py importar_catalogo catalogo_seriart.xlsx
    python manage.py importar_catalogo catalogo_seriart.xlsx --generacion 2027 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from apps.catalogo.importador import HOJA, ImportacionError, importar_catalogo


class Command(BaseCommand):
    help = "Importa secciones, modelos, colores, tamaños, variantes, productos y precios desde el Excel."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta al .xlsx")
        parser.add_argument("--hoja", default=HOJA)
        parser.add_argument(
            "--generacion",
            type=int,
            help="Año de la generación. Si se omite, se lee del encabezado 'PRECIO <año>'.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Muestra el resultado sin guardar nada.")

    def handle(self, *args, **opts):
        try:
            anio, resumen, avisos = importar_catalogo(
                opts["archivo"], anio=opts["generacion"], hoja=opts["hoja"], dry_run=opts["dry_run"]
            )
        except ImportacionError as exc:
            for e in exc.errores:
                self.stderr.write(self.style.ERROR(e))
            raise CommandError(str(exc)) from exc

        for aviso in avisos:
            self.stdout.write(self.style.WARNING(f"  Aviso: {aviso}"))
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardó nada."))
        for clave, valor in resumen.items():
            self.stdout.write(f"  {clave}: {valor}")
        self.stdout.write(self.style.SUCCESS(f"Catálogo importado para la generación {anio}."))
