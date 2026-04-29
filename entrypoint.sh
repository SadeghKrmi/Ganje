#!/bin/bash
set -e

echo "Waiting for database..."
python -c "
import time, os, psycopg2
from urllib.parse import urlparse

url = urlparse(os.environ.get('DATABASE_URL', ''))
while True:
    try:
        conn = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port or 5432,
        )
        conn.close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
"

echo "Running migrations..."
python manage.py migrate --noinput

# ── Auto-create initial superuser if env vars are set ──────────
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Bootstrapping initial superuser ($DJANGO_SUPERUSER_EMAIL)..."
  python manage.py shell <<PY
from django.contrib.auth import get_user_model
import os

U = get_user_model()
email = os.environ["DJANGO_SUPERUSER_EMAIL"].strip().lower()
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", email.split("@")[0]).strip()

user, created = U.objects.get_or_create(
    email=email,
    defaults={"username": username, "is_staff": True, "is_superuser": True},
)
if created:
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"  ✓ Created superuser {email}")
else:
    print(f"  · Superuser {email} already exists; leaving password unchanged")
PY
fi

echo "Starting server..."
exec python manage.py runserver 0.0.0.0:8000
