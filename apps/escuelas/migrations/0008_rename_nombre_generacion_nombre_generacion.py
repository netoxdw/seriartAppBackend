from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("escuelas", "0007_remove_grupo_grupo_unico_por_escuela_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="generacion",
            old_name="nombre",
            new_name="nombre_generacion",
        ),
    ]
