from urllib.parse import urlparse

import dj_database_url
from decouple import config

from .base import *  # noqa: F401,F403
from .database import require_database_url


def _csv_env(name):
    return [item.strip() for item in config(name, default="").split(",") if item.strip()]


def _csv_env_values(*names):
    values = []
    for name in names:
        values.extend(_csv_env(name))
    return values


def _configured_values(*names):
    return [value for value in (config(name, default="").strip() for name in names) if value]


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def _https_origin(value):
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _normalized_host(value):
    if not value:
        return ""
    value = value.strip()
    if value.startswith("."):
        return value
    normalized = value if "://" in value else f"https://{value}"
    return urlparse(normalized).hostname or value


def _cloudinary_config():
    values = {
        "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default="").strip(),
        "API_KEY": config("CLOUDINARY_API_KEY", default="").strip(),
        "API_SECRET": config("CLOUDINARY_API_SECRET", default="").strip(),
    }
    return values if all(values.values()) else None


DEBUG = False

DEFAULT_PUBLIC_API_DOMAIN = "api.magnivel.org"
DEFAULT_FRONTEND_ORIGINS = [
    "https://magnivelinternational.org",
    "https://www.magnivelinternational.org",
    "https://frontend-mm.vercel.app",
]
DEFAULT_ADMIN_FRONTEND_ORIGINS = ["https://admin.magnivelinternational.org"]

CONFIGURED_FRONTEND_ORIGINS = _unique(
    [
        *_csv_env_values("CORS_ALLOWED_ORIGINS", "FRONTEND_URLS"),
        *_configured_values("FRONTEND_URL", "ADMIN_FRONTEND_URL"),
    ]
)

if not CONFIGURED_FRONTEND_ORIGINS:
    CONFIGURED_FRONTEND_ORIGINS = _unique(
        [
            *DEFAULT_FRONTEND_ORIGINS,
            *DEFAULT_ADMIN_FRONTEND_ORIGINS,
        ]
    )

ALLOWED_HOSTS = _unique(
    [
        "localhost",
        "127.0.0.1",
        ".railway.app",
        ".up.railway.app",
        _normalized_host(DEFAULT_PUBLIC_API_DOMAIN),
        *[_normalized_host(value) for value in _csv_env("ALLOWED_HOSTS")],
        *[
            _normalized_host(value)
            for value in _configured_values(
                "RAILWAY_PUBLIC_DOMAIN",
                "RAILWAY_PRIVATE_DOMAIN",
                "CUSTOM_DOMAIN",
            )
        ],
    ]
)

DATABASES = {
    "default": dj_database_url.parse(
        require_database_url(),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

CORS_ALLOWED_ORIGINS = CONFIGURED_FRONTEND_ORIGINS

CSRF_TRUSTED_ORIGINS = _unique(
    [
        *CORS_ALLOWED_ORIGINS,
        *_csv_env_values("CSRF_TRUSTED_ORIGINS"),
        _https_origin(config("CUSTOM_DOMAIN", default=DEFAULT_PUBLIC_API_DOMAIN).strip()),
        *[
            _https_origin(value)
            for value in _configured_values("RAILWAY_PUBLIC_DOMAIN", "CUSTOM_DOMAIN")
        ],
    ]
)

_cloudinary = _cloudinary_config()
if _cloudinary:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    CLOUDINARY_STORAGE = _cloudinary

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="").strip()
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="").strip()

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=3600, cast=int)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
