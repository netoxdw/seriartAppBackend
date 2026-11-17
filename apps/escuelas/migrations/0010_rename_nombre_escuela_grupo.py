from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("escuelas", "0009_escuela_nivel"),
    ]

    operations = [
        # La restricción usa el campo "nombre": se quita, se renombra y se vuelve a crear.
        migrations.RemoveConstraint(
            model_name="grupo",
            name="grupo_unico_por_escuela_generacion",
        ),
        migrations.RenameField(
            model_name="escuela",
            old_name="nombre",
            new_name="nombre_escuela",
        ),
        migrations.RenameField(
            model_name="grupo",
            old_name="nombre",
            new_name="nombre_grupo",
        ),
        migrations.AlterModelOptions(
            name="grupo",
            options={"ordering": ["escuela", "nombre_grupo"]},
        ),
        migrations.AddConstraint(
            model_name="grupo",
            constraint=models.UniqueConstraint(
                fields=("nombre_grupo", "escuela", "generacion"),
                name="grupo_unico_por_escuela_generacion",
            ),
        ),
    ]
