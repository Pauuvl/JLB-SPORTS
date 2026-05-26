#!/usr/bin/env bash
# Script de construcción para Render

set -o errexit  # Detener si hay error

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

# Cargar datos iniciales si existen
if [ -f "fixtures/initial_products.json" ]; then
    python manage.py loaddata fixtures/initial_products.json || true
fi
if [ -f "fixtures/initial_clients.json" ]; then
    python manage.py loaddata fixtures/initial_clients.json || true
fi
