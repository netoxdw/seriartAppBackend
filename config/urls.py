from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from apps.core.views import HomeView, GeneracionCreateView

urlpatterns = [

    # ADMIN
    path('admin/', admin.site.urls),

    # AUTH
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

    # HOME
    path('', HomeView.as_view(), name='home'),

    # GENERACIONES
    path(
        'generaciones/nueva/',
        GeneracionCreateView.as_view(),
        name='generacion_create'
    ),

    # APPS
    path('', include('apps.escuelas.urls')),
    path('', include('apps.alumnos.urls')),
    path('', include('apps.ventas.urls')),
]