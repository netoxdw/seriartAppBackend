from django.urls import path
from .views import GeneracionDetailView

urlpatterns = [
    path('generaciones/<int:pk>/', GeneracionDetailView.as_view(), name='generacion_detail'),
]