# ⚽ JLB Sports — Sistema de Gestión Comercial

Sistema completo de gestión de inventario y ventas, desarrollado con **Django 4.2**.

---

## 🚀 Inicio Rápido

### 1. Crear y activar entorno virtual

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate
```

> ⚠️ Si PowerShell muestra error de permisos ejecute primero:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configuración automática

```bash
python setup.py
```

Ejecuta automáticamente: migraciones, datos de muestra y superusuario.

### 4. Iniciar el servidor

```bash
python manage.py runserver
```

### 5. Abrir en el navegador

- **Sistema:** http://127.0.0.1:8000/
- **Admin:**   http://127.0.0.1:8000/admin/

---

## 🔑 Credenciales

| Usuario | Contraseña |
|---------|------------|
| `admin` | `admin1234` |

---

## 🗂️ Módulos

| Módulo | Funcionalidades |
|--------|----------------|
| 📦 **Inventario** | CRUD productos, categorías, alertas de stock mínimo, análisis de márgenes |
| 🧾 **Ventas** | Constructor dinámico, descuentos por cliente, anulación con restauración de stock |
| 👥 **Clientes** | 4 tipos (Regular/VIP/Empresa/Mayorista), descuentos automáticos, historial |
| 📋 **Pedidos** | Flujo pendiente → confirmado, stock no se afecta hasta confirmar |
| 💰 **Precios** | Análisis costo vs venta, listas de precios personalizadas |

---

## ⚙️ Reglas de Negocio

- El stock se descuenta **en tiempo real** al confirmar una venta
- Los pedidos **NO reducen el inventario** hasta ser confirmados
- No se puede vender si el stock es insuficiente (error controlado)
- Los precios varían automáticamente según el tipo de cliente

---

*JLB Sports — Proyecto de Ingeniería de Software · Django 4.2*
