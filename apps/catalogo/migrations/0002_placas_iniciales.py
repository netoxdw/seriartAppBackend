from django.db import migrations

# Las placas que antes estaban fijas en PedidoItemBase.PLACA_CHOICES.
PLACAS = [
    "Arena",
    "Mediterránea",
    "4 piezas",
    "Extendida",
    "Corte plano",
    "Palermo",
    "Círculo",
    "Corazón",
    "Estrella",
    "Columnas",
    "Pergamino",
]


def crear_placas(apps, schema_editor):
    Placa = apps.get_model("catalogo", "Placa")
    for orden, nombre in enumerate(PLACAS, start=1):
        Placa.objects.get_or_create(nombre=nombre, defaults={"orden": orden})


def borrar_placas(apps, schema_editor):
    apps.get_model("catalogo", "Placa").objects.filter(nombre__in=PLACAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_placas, borrar_placas),
    ]
