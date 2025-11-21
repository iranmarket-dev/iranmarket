# iranmarket/settings_base.py
from pathlib import Path
import os

from dotenv import load_dotenv
import dj_database_url  # برای پارس کردن DATABASE_URL (Render / Postgres)

# ---------- BASE DIR & ENV ----------

BASE_DIR = Path(__file__).resolve().parent.parent

# خواندن متغیرها از فایل .env کنار manage.py (برای توسعه روی سیستم خودت)
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """
    خواندن مقدار بولین از ENV
    مثال:
        DJANGO_DEBUG=true / True / 1 / yes
    """
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "t", "yes", "y")


# ---------- CORE SETTINGS ----------

# SECRET_KEY
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-unsafe")

# DEBUG
DEBUG = env_bool("DJANGO_DEBUG", True)

# در محیط غیر دیباگ، حتما باید SECRET_KEY امن از ENV بگیری
if not DEBUG and SECRET_KEY == "dev-secret-key-unsafe":
    raise RuntimeError(
        "در محیط غیر دیباگ باید DJANGO_SECRET_KEY در ENV تنظیم شود."
    )

# ALLOWED_HOSTS
# مثال در Render:
# DJANGO_ALLOWED_HOSTS=iranmarket.onrender.com
if DEBUG:
    ALLOWED_HOSTS: list[str] = []
else:
    hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
    ALLOWED_HOSTS = [h.strip() for h in hosts.split(",") if h.strip()]

# برای CSRF در پروداکشن (آدرس کامل با https)
# مثال:
# DJANGO_CSRF_TRUSTED_ORIGINS=https://iranmarket.onrender.com
csrf_env = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in csrf_env.split(",")
    if origin.strip()
]


# ---------- APPS ----------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # اپ فروشگاه
    "shop",
]


# ---------- MIDDLEWARE ----------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # برای سرو استاتیک‌ها در Render / پروداکشن
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "iranmarket.urls"


# ---------- TEMPLATES ----------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # اگر templates جدا داری، این مسیر خوبه؛
        # اگر نه، می‌تونی خالی بذاری []
        "DIRS": [BASE_DIR / "shop" / "templates"],

        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # برای دسته‌ها و تنظیمات فروشگاه
                "shop.context_processors.global_store_context",
                "shop.context_processors.city_context",
            ],
        },
    },
]


WSGI_APPLICATION = "iranmarket.wsgi.application"


# ---------- DATABASES ----------

# ۱) اگر DATABASE_URL در ENV باشد (Render / Postgres)، همان استفاده می‌شود.
# ۲) اگر نه، از سیستم قبلی‌ات (DJANGO_DB_ENGINE=sqlite/postgres) استفاده می‌شود.

database_url = os.getenv("DATABASE_URL")

if database_url:
    # حالت Render / هر جایی که DATABASE_URL داری
    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=60,
        )
    }
else:
    # سیستم قبلی‌ات (برای توسعه روی لوکال)
    DB_ENGINE = os.getenv("DJANGO_DB_ENGINE", "sqlite").lower()

    if DB_ENGINE == "postgres":
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DJANGO_DB_NAME", "iranmarket"),
                "USER": os.getenv("DJANGO_DB_USER", ""),
                "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", ""),
                "HOST": os.getenv("DJANGO_DB_HOST", "localhost"),
                "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
                "CONN_MAX_AGE": 60,  # اتصال‌های پایدارتر
            }
        }
    else:
        # حالت پیش‌فرض: sqlite (همینی که فعلاً می‌خوای)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / os.getenv("DJANGO_DB_NAME", "db.sqlite3"),
            }
        }


# ---------- PASSWORD VALIDATORS ----------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ---------- INTERNATIONALIZATION ----------

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


# ---------- STATIC & MEDIA ----------

STATIC_URL = "/static/"

# چون استاتیک‌ها را گذاشتی داخل shop/static
STATICFILES_DIRS = [
    BASE_DIR / "shop" / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# برای WhiteNoise در پروداکشن
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CART_SESSION_ID = "cart"

# ---------- DEFAULT PRIMARY KEY ----------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "IranMarket <no-reply@iranmarket.local>"
