from django.urls import path
from .views import GeneracionDetailView, EscuelaCreateView

urlpatterns = [
    path('generaciones/<int:pk>/', GeneracionDetailView.as_view(), name='generacion_detail'),
    path('generaciones/<int:pk>/nueva-escuela/', EscuelaCreateView.as_view(), name='escuela_create'),
]