from django.db import models
from inventory.models import Product
from clients.models import Client
from django.db import transaction


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('converted', 'Convertido a Venta'),
        ('cancelled', 'Cancelado'),
    ]

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        client_name = self.client.name if self.client else 'Mostrador'
        return f"Pedido #{self.pk} - {client_name} ({self.get_status_display()})"

    def calculate_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()

    def confirm(self):
        from django.utils import timezone
        with transaction.atomic():
            for item in self.items.all():
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                if product.stock_quantity < item.quantity:
                    raise ValueError(
                        f'Stock insuficiente para "{product.name}". '
                        f'Disponible: {product.stock_quantity}, Requerido: {item.quantity}'
                    )
                product.stock_quantity -= item.quantity
                product.save()
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
