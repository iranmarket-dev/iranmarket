#!/usr/bin/env bash
set -o errexit  # اگر خطا شد، دیپلوی متوقف شود

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
