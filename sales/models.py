from django.db import models
from inventory.models import Product
from clients.models import Client


class Sale(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        client_name = self.client.name if self.client else 'Mostrador'
        return f"Venta #{self.pk} - {client_name} - ${self.total_amount}"

    def calculate_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    color_vendido = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Color vendido'
    )

    def __str__(self):
        color_str = f' ({self.color_vendido})' if self.color_vendido else ''
        return f"{self.product.name}{color_str} x{self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
