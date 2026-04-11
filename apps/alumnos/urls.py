from django.urls import path
from .views import GrupoDetailView, AlumnoCreateView, AlumnoUpdateView, AlumnoDetailView

urlpatterns = [
    path('grupos/<int:pk>/', GrupoDetailView.as_view(), name='grupo_detail'),
    path('grupos/<int:grupo_id>/nuevo/', AlumnoCreateView.as_view(), name='alumno_create'),
    path('alumnos/<int:pk>/editar/', AlumnoUpdateView.as_view(), name='alumno_update'),
    path('alumnos/<int:pk>/', AlumnoDetailView.as_view(), name='alumno_detail'),
]