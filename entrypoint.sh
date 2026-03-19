#!/bin/bash
set -e

echo "[HomeDash] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.environ.get('DB_HOST','localhost'),
        port=os.environ.get('DB_PORT','5432'),
        dbname=os.environ.get('DB_NAME','homedash'),
        user=os.environ.get('DB_USER','admin'),
        password=os.environ.get('DB_PASSWORD','admin'),
    )
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "[HomeDash] PostgreSQL ready."

echo "[HomeDash] Running migrations..."
python manage.py migrate --noinput

echo "[HomeDash] Creating default admin user (if not exists)..."
python manage.py shell -c "
from django.contrib.auth.models import User
import os
username = os.environ.get('ADMIN_USER', 'admin')
password = os.environ.get('ADMIN_PASSWORD', 'admin')
email    = os.environ.get('ADMIN_EMAIL', 'admin@homedash.local')
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(username, email, password)
    print(f'[HomeDash] Superuser {username!r} created.')
else:
    print('[HomeDash] Superuser already exists.')
"

exec "$@"
