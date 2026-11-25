"""Django settings for PO Tracker. All secrets come from environment (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # required; never hardcoded
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "apps.accounts",
    "apps.dashboard",
    "apps.customers",
    "apps.materials",
    "apps.inbox",
    "apps.ocr",
    "apps.purchase_orders",
    "apps.supply_tracking",
    "apps.reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL is the only business database.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "po_tracker"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        # Reuse the connection between requests: opening one costs several network round trips.
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0" if DEBUG else "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.accounts.permissions.RoleBasedPermission"],
    "DEFAULT_PAGINATION_CLASS": "apps.accounts.pagination.StandardPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.api_exception_handler",
}

# CORS / CSRF for local React development (Vite proxies /api, so same-origin by default)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
# Allow the PDF/image preview iframe inside the React app (same origin through the Vite proxy)
X_FRAME_OPTIONS = "SAMEORIGIN"

# OCR
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "").strip()
OCR_LANG = os.environ.get("OCR_LANG", "eng").strip() or "eng"  # e.g. tha+eng (needs tha.traineddata)
# On Linux (Vercel) use the Tesseract bundled in backend/vendor/tesseract when no path is set
# (built by tools/build-tesseract.sh). Windows keeps using TESSERACT_CMD / PATH.
_VENDOR_TESS = BASE_DIR / "vendor" / "tesseract"
if not TESSERACT_CMD and os.name != "nt" and (_VENDOR_TESS / "bin" / "tesseract").exists():
    TESSERACT_CMD = str(_VENDOR_TESS / "bin" / "tesseract")
    os.environ["LD_LIBRARY_PATH"] = f"{_VENDOR_TESS / 'lib'}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ.setdefault("TESSDATA_PREFIX", str(_VENDOR_TESS / "tessdata"))

# Uploaded files: Cloudflare R2 (S3-compatible) when configured, otherwise local MEDIA_ROOT.
# Vercel's filesystem is read-only, so production must set the AWS_* variables.
if os.environ.get("AWS_STORAGE_BUCKET_NAME"):
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"],
                "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL") or None,
                "region_name": os.environ.get("AWS_S3_REGION_NAME", "auto"),
                "access_key": os.environ.get("AWS_ACCESS_KEY_ID"),
                "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
                "signature_version": "s3v4",
                "default_acl": None,
                "file_overwrite": False,
                "querystring_auth": True,
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
# Inbox
INBOX_MODE = os.environ.get("INBOX_MODE", "demo").lower()  # demo | live
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
MS_GRAPH_CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID", "")
MS_GRAPH_CLIENT_SECRET = os.environ.get("MS_GRAPH_CLIENT_SECRET", "")
MS_GRAPH_TENANT_ID = os.environ.get("MS_GRAPH_TENANT_ID", "")
GMAIL_REDIRECT_URI = os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/inbox/oauth/gmail/callback/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
