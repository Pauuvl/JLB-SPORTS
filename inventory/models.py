from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):

    codigo = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        default=None,
        verbose_name='Código'
    )

    name = models.CharField(max_length=200)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    talla = models.CharField(
        max_length=20,
        blank=True,
        default=''
    )

    color = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Color(es)',
        help_text='Colores disponibles separados por coma. Ej: Rojo, Azul, Negro'
    )

    description = models.TextField(blank=True)

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock_quantity = models.IntegerField(default=0)

    min_stock = models.IntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        parts = [self.name]
        if self.talla:
            parts.append(f'T:{self.talla}')
        if self.color:
            parts.append(f'C:{self.color}')
        return ' | '.join(parts)

    def get_colores_lista(self):
        """Retorna lista de colores disponibles."""
        if self.color:
            return [c.strip() for c in self.color.split(',') if c.strip()]
        return []

    @property
    def stock_value(self):
        return self.cost_price * self.stock_quantity

    @property
    def is_low_stock(self):
        return (
            self.stock_quantity > 0 and
            self.stock_quantity <= self.min_stock
        )

    @property
    def profit_margin(self):
        if self.cost_price and self.cost_price > 0:
            return ((self.sale_price - self.cost_price) / self.cost_price) * 100
        return 0
