from django.db import models
from inventory.models import Product
from clients.models import Client


class PriceList(models.Model):
    name = models.CharField(max_length=100)
    client_type = models.CharField(max_length=20, choices=Client.CLIENT_TYPES, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['price_list', 'product']

    def __str__(self):
        return f"{self.price_list.name} - {self.product.name}: ${self.custom_price}"
