from django.urls import path
from .views import GrupoDetailView, AlumnoCreateView

urlpatterns = [
    path('grupos/<int:pk>/', GrupoDetailView.as_view(), name='grupo_detail'),
    path('grupos/<int:grupo_id>/nuevo/', AlumnoCreateView.as_view(), name='alumno_create'),
]