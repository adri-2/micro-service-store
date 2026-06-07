"""
Development settings
Inherits from base settings and overrides for development environment
"""

from datetime import timedelta
from .base import *


DEBUG = True
ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CORS_ALLOW_ALL_ORIGINS = True

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=200),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ALGORITHM": env_or_default("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": env_or_default("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer","JWT"),
    "ISSUER": config("JWT_ISSUER", default="account-service"),
    "AUDIENCE": config("JWT_AUDIENCE", default="store-front-services"),
}
