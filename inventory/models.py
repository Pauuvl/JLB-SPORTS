from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):

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
        return self.name

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
        """Margen de ganancia en porcentaje sobre el costo."""
        if self.cost_price and self.cost_price > 0:
            return ((self.sale_price - self.cost_price) / self.cost_price) * 100
        return 0
