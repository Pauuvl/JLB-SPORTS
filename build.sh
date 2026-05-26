#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

# Cargar datos desde la base de datos local exportada
if [ -f "fixtures/initial_data.json" ]; then
    python manage.py loaddata fixtures/initial_data.json || true
fi

# Crear superusuario desde variables de entorno si no existe
python manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@jlbsports.com')
if password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password, email=email)
    print(f"Superusuario '{username}' creado.")
else:
    print("Superusuario ya existe o no se configuró contraseña.")
PYEOF
