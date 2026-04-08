from django.urls import path
from .views import GeneracionDetailView, EscuelaCreateView, EscuelaDetailView, GrupoCreateView, GrupoUpdateView

urlpatterns = [
    path('generaciones/<int:pk>/', GeneracionDetailView.as_view(), name='generacion_detail'),
    path('generaciones/<int:pk>/nueva-escuela/', EscuelaCreateView.as_view(), name='escuela_create'),
    path('generaciones/<int:generacion_id>/escuelas/<int:pk>/', EscuelaDetailView.as_view(), name='escuela_detail'),
    path('generaciones/<int:generacion_id>/escuelas/<int:escuela_id>/grupos/nuevo/', GrupoCreateView.as_view(), name='grupo_create'),
    path('grupos/<int:pk>/editar/', GrupoUpdateView.as_view(), name='grupo_update'),
]