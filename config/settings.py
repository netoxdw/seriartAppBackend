from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


# Seguridad
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

# Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'import_export',  # ← agrega esto

    'apps.escuelas',
    'apps.alumnos',
    'apps.catalogo',
    'apps.ventas',
    'apps.core',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Base de datos (.env)
# Producción: MySQL. Desarrollo local sin MySQL: DB_ENGINE=sqlite
if config('DB_ENGINE', default='mysql') == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
        }
    }

# Base de datos de la versión 1 (solo para `manage.py migrar_desde_v1`).
# Misma conexión que la principal, otra base: DB_V1_NAME=seriart_v1
if config('DB_V1_NAME', default=''):
    DATABASES['v1'] = {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_V1_NAME'),
        'USER': config('DB_V1_USER', default=config('DB_USER', default='')),
        'PASSWORD': config('DB_V1_PASSWORD', default=config('DB_PASSWORD', default='')),
        'HOST': config('DB_V1_HOST', default=config('DB_HOST', default='localhost')),
        'PORT': config('DB_V1_PORT', default=config('DB_PORT', default='3306')),
    }

# Validación de passwords
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalización
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# =========================
# AUTHENTICATION
# =========================

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# =========================
# SESSION CONFIG
# =========================

# 24 horas
SESSION_COOKIE_AGE = 86400

# mantener sesión al cerrar navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# renovar expiración en cada request
SESSION_SAVE_EVERY_REQUEST = True


# =========================
# SECURITY PRODUCTION
# =========================

# HTTPS=True en el .env cuando el sitio se sirve con certificado (nginx hace la redirección)
HTTPS = config('HTTPS', default=False, cast=bool)
CSRF_COOKIE_SECURE = HTTPS
SESSION_COOKIE_SECURE = HTTPS

# Ej.: CSRF_TRUSTED_ORIGINS=https://seriartapp.tech,https://www.seriartapp.tech
CSRF_TRUSTED_ORIGINS = [o for o in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if o]

SECURE_SSL_REDIRECT = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = 'DENY'