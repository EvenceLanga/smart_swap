import dj_database_url
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Security - Use environment variable in production
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-9w+#hdh+)&g258dvqk=!#h(_o!me&+bexwdt6+*_7z6l%&z_(-')

# Debug - False in production
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Allowed Hosts
ALLOWED_HOSTS = [
    'smartswap-production-611b.up.railway.app',
    '.railway.app',
    'localhost',
    '127.0.0.1',
    '.up.railway.app',
]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'https://smartswap-production-611b.up.railway.app',
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://localhost',
    'http://127.0.0.1',
]

# Additional CSRF settings
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = True
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://smartswap-production-611b.up.railway.app",
    "https://*.railway.app",
    "https://*.up.railway.app",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all in development

# Session settings
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Installed Apps
INSTALLED_APPS = [
    'corsheaders',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',

    # local apps
    'core.apps.CoreConfig',
]

# ASGI Application
ASGI_APPLICATION = 'skillswap_django_project.asgi.application'

# Channel layer for local dev (use Redis in production)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL Configuration
ROOT_URLCONF = 'skillswap_project.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notification_counts',
            ],
        },
    },
]

# WSGI Application
WSGI_APPLICATION = 'skillswap_project.wsgi.application'

# Database Configuration
if os.getenv('DATABASE_URL'):
    # Use Railway's database
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Fallback for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    # Development settings
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False


LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'core:dashboard'  
LOGOUT_REDIRECT_URL = 'core:index'     
SECURE_SSL_REDIRECT = False


# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'da16.domains.co.za'
EMAIL_PORT = 465
EMAIL_USE_SSL = True  # Use SSL for port 465
EMAIL_USE_TLS = False  # Disable TLS when using SSL
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'info@novatechsupplies.co.za'  # Must match EMAIL_HOST_USER
SERVER_EMAIL = 'info@novatechsupplies.co.za'

# For development - use console backend
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'