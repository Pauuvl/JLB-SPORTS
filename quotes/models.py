from django.db import models
from inventory.models import Product
from clients.models import Client


class Quote(models.Model):
    STATUS_CHOICES = [
        ('draft',    'Borrador'),
        ('sent',     'Enviada'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
    ]
    client       = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')
    client_name  = models.CharField(max_length=200, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes        = models.TextField(blank=True)
    valid_days   = models.PositiveIntegerField(default=15)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cotizacion #{self.pk} — {self.display_client}"

    def calculate_total(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.save()

    @property
    def display_client(self):
        if self.client:
            return self.client.name
        return self.client_name or 'Sin cliente'


class QuoteItem(models.Model):
    quote       = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    product     = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=300)
    quantity    = models.PositiveIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
