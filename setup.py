#!/usr/bin/env python
"""
JLB Sports — First-time setup script.
Run this after pip install to prepare the database,
load sample data, and create a superuser automatically.
"""
import os
import sys
import subprocess

def run(cmd, **kwargs):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, **kwargs)
    if result.returncode != 0:
        print(f"  ❌ Command failed: {cmd}")
        sys.exit(1)

def main():
    print("\n" + "="*52)
    print("  JLB Sports — Setup Wizard")
    print("="*52 + "\n")

    # 1. Migrations
    print("📦 Running database migrations...")
    run("python manage.py makemigrations")
    run("python manage.py migrate")
    print("  ✅ Database ready\n")

    # 2. Load fixtures
    print("📂 Loading sample data...")
    run("python manage.py loaddata fixtures/initial_products.json")
    run("python manage.py loaddata fixtures/initial_clients.json")
    print("  ✅ Sample data loaded\n")

    # 3. Create superuser
    print("👤 Creating admin superuser...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jlb_sports.settings')

    import django
    django.setup()
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@jlbsports.com', 'admin1234')
        print("  ✅ Superuser created: admin / admin1234\n")
    else:
        print("  ⚠️  Superuser 'admin' already exists, skipping.\n")

    print("="*52)
    print("  ✅ Setup complete!")
    print("="*52)
    print("\n  👉 Start the server:")
    print("     python manage.py runserver\n")
    print("  🌐 Open:  http://127.0.0.1:8000/")
    print("  🔑 Admin: http://127.0.0.1:8000/admin/")
    print("            username: admin  |  password: admin1234\n")

if __name__ == '__main__':
    main()
