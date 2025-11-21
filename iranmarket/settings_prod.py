# iranmarket/settings_prod.py
from .settings_base import *

# تنظیمات مخصوص محیط واقعی (سرور)
DEBUG = False

# این‌جا بعداً دامنه واقعی‌ات را می‌گذاری
ALLOWED_HOSTS = ["yourdomain.com"]

# بعداً این‌جا تنظیمات امنیتی و دیتابیس PostgreSQL رو اضافه می‌کنیم
