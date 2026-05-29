#!/usr/bin/env bash
set -o errexit

echo "📦 Instalando dependencias..."
pip install -r requirements.txt

echo "🗂️  Recolectando archivos estáticos..."
python manage.py collectstatic --no-input

echo "🗃️  Aplicando migraciones..."
python manage.py migrate

echo "📥 Cargando datos iniciales..."
if [ -f "fixtures/initial_data.json" ]; then
    python manage.py loaddata fixtures/initial_data.json || echo "⚠️  Fixture ya cargado o con conflicto, continuando..."
else
    echo "ℹ️  No se encontró fixtures/initial_data.json, omitiendo."
fi

echo "👤 Creando superusuario si no existe..."
python manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@jlbsports.com')

if not password:
    print("⚠️  DJANGO_SUPERUSER_PASSWORD no configurada, omitiendo creación.")
elif User.objects.filter(username=username).exists():
    print(f"ℹ️  El usuario '{username}' ya existe.")
else:
    User.objects.create_superuser(username=username, password=password, email=email)
    print(f"✅ Superusuario '{username}' creado.")
PYEOF

echo "✅ Build completado."
