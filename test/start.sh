#!/bin/sh
# Live, browsable NetBox with the netbox_k3s plugin enabled.
set -e
cd /opt/netbox/netbox
export PYTHONPATH=/source

echo ">>> Applying migrations..."
python manage.py migrate --no-input

echo ">>> Creating superuser admin/admin (if absent)..."
DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser \
  --noinput --username admin --email admin@example.com 2>/dev/null || true

echo ">>> Seeding example k3s data..."
python manage.py shell -c "exec(open('/seed.py').read())" || true

echo ">>> Starting NetBox at http://localhost:8080  (login: admin / admin)"
exec python manage.py runserver 0.0.0.0:8080 --insecure --noreload
