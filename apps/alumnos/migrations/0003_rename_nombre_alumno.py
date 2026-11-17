from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alumnos", "0002_alumno_alumno_unico_por_grupo"),
    ]

    operations = [
        # La restricción usa el campo "nombre": se quita, se renombra y se vuelve a crear.
        migrations.RemoveConstraint(
            model_name="alumno",
            name="alumno_unico_por_grupo",
        ),
        migrations.RenameField(
            model_name="alumno",
            old_name="nombre",
            new_name="nombre_alumno",
        ),
        migrations.AddConstraint(
            model_name="alumno",
            constraint=models.UniqueConstraint(
                fields=("nombre_alumno", "grupo"),
                name="alumno_unico_por_grupo",
            ),
        ),
    ]
