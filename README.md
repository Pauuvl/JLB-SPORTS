# JLB Sports - Sistema de Gestión

Sistema de gestión de ventas, inventario y clientes para JLB Sports.

## Módulos
- **Inventario**: Productos, categorías, marcas
- **Clientes**: Gestión de clientes por tipo
- **Pedidos**: Creación y seguimiento de pedidos
- **Ventas**: Registro de ventas
- **Cotizaciones**: Generación de cotizaciones
- **Precios**: Listas de precios por tipo de cliente

## Despliegue en Render

1. Sube este proyecto a GitHub
2. Ve a [render.com](https://render.com) y crea una cuenta
3. Clic en **New → Web Service**
4. Conecta tu repositorio de GitHub
5. Render detectará automáticamente el `render.yaml`
6. Las variables de entorno se configuran solas

## Variables de entorno requeridas
- `SECRET_KEY` — Render la genera automáticamente
- `DEBUG` — Debe ser `False` en producción
- `ALLOWED_HOSTS` — Tu dominio en Render (`.onrender.com`)

## Desarrollo local
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
