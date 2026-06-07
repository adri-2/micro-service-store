"""
Production settings
Inherits from base settings and overrides for production environment
"""



import os

from .base import *
from datetime import timedelta
from pathlib import Path
from decouple import config
import dj_database_url

def env_or_default(name, default):
    value = config(name, default=default)
    return default if str(value).strip() == "" else value


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Add your production domain here
ALLOWED_HOSTS = env_or_default('ALLOWED_HOSTS','').split(',')

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


DB_URL = config("DATABASE_URL", default="postgresql://account_user:account_pass@db/account_db")
DATABASES = {}


DATABASES["default"] = dj_database_url.config(
    default=DB_URL,
    conn_max_age=60,
)


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=7, cast=int)),
    "ALGORITHM": env_or_default("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": env_or_default("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer","JWT"),
    "ISSUER": config("JWT_ISSUER", default="account-service"),
    "AUDIENCE": config("JWT_AUDIENCE", default="store-front-services"),
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/


STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Logging
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
