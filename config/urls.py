from django.contrib import admin
from django.urls import path, include
from apps.core.views import HomeView, GeneracionCreateView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('generaciones/nueva/', GeneracionCreateView.as_view(), name='generacion_create'),
    path('', include('apps.escuelas.urls')),
    path('', include('apps.alumnos.urls')),
]