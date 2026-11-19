"""Cada tamaño dice qué va en él: diploma/agradecimiento o foto panorámica."""
from django.db import migrations, models

INICIALES = {
    "CARTA": "diploma_agradecimiento",
    "DOBLE ESPACIO": "diploma_agradecimiento",
    "ESTANDAR": "panoramica",
    "AMPLIADA": "panoramica",
}


def adelante(apps, schema_editor):
    Tamano = apps.get_model("catalogo", "Tamano")
    for nombre, concepto in INICIALES.items():
        Tamano.objects.filter(nombre=nombre, concepto="").update(concepto=concepto)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_tamano_panoramica_a_estandar"),
    ]

    operations = [
        migrations.AddField(
            model_name="tamano",
            name="concepto",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Sin definir"),
                    ("diploma_agradecimiento", "Diploma / agradecimiento"),
                    ("panoramica", "Foto panorámica"),
                ],
                default="",
                help_text="Qué va en este tamaño; decide las opciones de la captura (columna CONCEPTO del Excel).",
                max_length=30,
            ),
        ),
        migrations.RunPython(adelante, migrations.RunPython.noop),
    ]
