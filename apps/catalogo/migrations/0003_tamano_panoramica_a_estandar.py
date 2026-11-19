"""El tamaño PANORAMICA ahora se llama ESTANDAR (la foto sigue siendo panorámica)."""
from django.db import migrations


def renombrar(apps, nuevo, viejo):
    Tamano = apps.get_model("catalogo", "Tamano")
    if Tamano.objects.filter(nombre=nuevo).exists():
        return
    Tamano.objects.filter(nombre=viejo).update(nombre=nuevo)


def adelante(apps, schema_editor):
    renombrar(apps, "ESTANDAR", "PANORAMICA")


def atras(apps, schema_editor):
    renombrar(apps, "PANORAMICA", "ESTANDAR")


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_placas_iniciales"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
