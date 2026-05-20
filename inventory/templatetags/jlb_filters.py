# inventory/templatetags/jlb_filters.py
# Filtros personalizados para JLB Sports
# Formato de pesos colombianos y utilidades de inventario

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def pesos(value):
    """
    Convierte un número al formato de pesos colombianos.
    Ejemplo: 500000 → $500.000 | 1250000 → $1.250.000
    """
    try:
        value = Decimal(str(value))
        # Convertir a entero si no tiene decimales relevantes
        if value == value.to_integral_value():
            formatted = f"{int(value):,}".replace(",", ".")
        else:
            # Si tiene decimales, mostrarlos
            formatted = f"{value:,.0f}".replace(",", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return f"${value}"


@register.filter
def pesos_plain(value):
    """Formato pesos sin símbolo $ para usar en inputs."""
    try:
        value = Decimal(str(value))
        formatted = f"{int(value):,}".replace(",", ".")
        return formatted
    except (ValueError, TypeError):
        return value


@register.filter
def stock_status(product):
    """Retorna el estado del stock como string."""
    if product.stock_quantity == 0:
        return "agotado"
    elif product.is_low_stock:
        return "bajo"
    return "ok"


@register.filter
def multiply(value, arg):
    """Multiplica dos valores."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def stock_badge(product):
    """Retorna HTML del badge de estado de stock."""
    if product.stock_quantity == 0:
        return '<span class="badge-stock agotado">Agotado</span>'
    elif product.is_low_stock:
        return f'<span class="badge-stock bajo">Stock Bajo ({product.stock_quantity})</span>'
    return f'<span class="badge-stock ok">{product.stock_quantity} und.</span>'
