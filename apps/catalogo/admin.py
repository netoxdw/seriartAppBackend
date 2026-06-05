from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

from .models import (
    Seccion,
    TamanoProducto,
    Modelo,
    PrecioBaseGeneracion,
    Anillo,
    PrecioAnilloGeneracion
)
from apps.escuelas.models import Generacion


# ========================
# RESOURCES
# ========================

class SeccionResource(resources.ModelResource):
    class Meta:
        model = Seccion
        fields = ('id', 'nombre')
        export_order = ('id', 'nombre')
        import_id_fields = ('nombre',)


class TamanoProductoResource(resources.ModelResource):
    class Meta:
        model = TamanoProducto
        fields = ('id', 'nombre')
        export_order = ('id', 'nombre')
        import_id_fields = ('nombre',)


class ModeloResource(resources.ModelResource):
    seccion = fields.Field(
        column_name='seccion',
        attribute='seccion',
        widget=ForeignKeyWidget(Seccion, field='nombre')
    )
    tamano_producto = fields.Field(
        column_name='tamano_producto',
        attribute='tamano_producto',
        widget=ForeignKeyWidget(TamanoProducto, field='nombre')
    )

    class Meta:
        model = Modelo
        fields = ('id', 'nombre', 'seccion', 'tamano_producto')
        export_order = ('id', 'nombre', 'seccion', 'tamano_producto')
        import_id_fields = ('nombre', 'seccion', 'tamano_producto')


class PrecioBaseGeneracionResource(resources.ModelResource):
    modelo = fields.Field(
        column_name='modelo',
        attribute='modelo',
        widget=ForeignKeyWidget(Modelo, field='id')
    )
    generacion = fields.Field(
        column_name='generacion',
        attribute='generacion',
        widget=ForeignKeyWidget(Generacion, field='anio')
    )
    # Campos auxiliares para leer del Excel (no se guardan en BD)
    seccion = fields.Field(column_name='seccion')
    tamano_producto = fields.Field(column_name='tamano_producto')

    class Meta:
        model = PrecioBaseGeneracion
        fields = ('id', 'modelo', 'seccion', 'tamano_producto', 'generacion', 'precio')
        export_order = ('id', 'modelo', 'seccion', 'tamano_producto', 'generacion', 'precio')
        import_id_fields = ('id',)

    def before_import_row(self, row, **kwargs):
        nombre = row.get('modelo')
        seccion = row.get('seccion')
        tamano = row.get('tamano_producto')

        if nombre and seccion and tamano:
            try:
                modelo = Modelo.objects.get(
                    nombre=nombre,
                    seccion__nombre=seccion,
                    tamano_producto__nombre=tamano
                )
                row['modelo'] = modelo.id
            except Modelo.DoesNotExist:
                pass
            except Modelo.MultipleObjectsReturned:
                pass

    def export_field(self, field, obj):
        # Al exportar, muestra nombre en vez de id para seccion y tamano
        if field.column_name == 'seccion':
            return obj.modelo.seccion.nombre
        if field.column_name == 'tamano_producto':
            return obj.modelo.tamano_producto.nombre
        if field.column_name == 'modelo':
            return obj.modelo.nombre
        return super().export_field(field, obj)


class AnilloResource(resources.ModelResource):
    modelo = fields.Field(
        column_name='modelo',
        attribute='modelo',
        widget=ForeignKeyWidget(Modelo, field='nombre')
    )

    class Meta:
        model = Anillo
        fields = ('id', 'modelo', 'metal')
        export_order = ('id', 'modelo', 'metal')
        import_id_fields = ('modelo', 'metal')


class PrecioAnilloGeneracionResource(resources.ModelResource):
    anillo = fields.Field(
        column_name='anillo',
        attribute='anillo',
        widget=ForeignKeyWidget(Anillo, field='id')
    )
    generacion = fields.Field(
        column_name='generacion',
        attribute='generacion',
        widget=ForeignKeyWidget(Generacion, field='anio')
    )
    # Campos auxiliares para leer del Excel
    anillo_modelo = fields.Field(column_name='anillo_modelo')
    anillo_metal = fields.Field(column_name='anillo_metal')

    class Meta:
        model = PrecioAnilloGeneracion
        fields = ('id', 'anillo', 'anillo_modelo', 'anillo_metal', 'generacion', 'precio')
        export_order = ('id', 'anillo_modelo', 'anillo_metal', 'generacion', 'precio')
        import_id_fields = ('id',)

    def before_import_row(self, row, **kwargs):
        modelo = row.get('anillo_modelo')
        metal = row.get('anillo_metal')

        if modelo and metal:
            try:
                anillo = Anillo.objects.get(modelo=modelo, metal=metal)
                row['anillo'] = anillo.id
            except Anillo.DoesNotExist:
                pass
            except Anillo.MultipleObjectsReturned:
                pass

    def export_field(self, field, obj):
        if field.column_name == 'anillo_modelo':
            return obj.anillo.modelo
        if field.column_name == 'anillo_metal':
            return obj.anillo.metal
        return super().export_field(field, obj)


# ========================
# ADMIN
# ========================

@admin.register(Seccion)
class SeccionAdmin(ImportExportModelAdmin):
    resource_class = SeccionResource
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(TamanoProducto)
class TamanoProductoAdmin(ImportExportModelAdmin):
    resource_class = TamanoProductoResource
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Modelo)
class ModeloAdmin(ImportExportModelAdmin):
    resource_class = ModeloResource
    list_display = ("nombre", "seccion", "tamano_producto")
    list_filter = ("seccion", "tamano_producto")
    search_fields = ("nombre",)


@admin.register(PrecioBaseGeneracion)
class PrecioBaseGeneracionAdmin(ImportExportModelAdmin):
    resource_class = PrecioBaseGeneracionResource
    list_display = ("modelo", "tamano_producto", "seccion", "generacion", "precio")
    list_filter = ("generacion", "modelo__seccion", "modelo__tamano_producto")
    search_fields = ("modelo__nombre",)

    def tamano_producto(self, obj):
        return obj.modelo.tamano_producto
    tamano_producto.short_description = "Tamaño"

    def seccion(self, obj):
        return obj.modelo.seccion
    seccion.short_description = "Sección"


@admin.register(Anillo)
class AnilloAdmin(ImportExportModelAdmin):
    resource_class = AnilloResource
    list_display = ("modelo", "metal")
    list_filter = ("metal",)
    search_fields = ("modelo__nombre",)  # corregido: era ("modelo",) sin lookup


@admin.register(PrecioAnilloGeneracion)
class PrecioAnilloGeneracionAdmin(ImportExportModelAdmin):
    resource_class = PrecioAnilloGeneracionResource
    list_display = ("anillo", "generacion", "precio")
    list_filter = ("generacion",)
    search_fields = ("anillo__modelo__nombre",)  # corregido también