from django.db import models


class Client(models.Model):
    CLIENT_TYPES = [
        ('regular', 'Regular'),
        ('Distribuidor', 'Distribuidor'),
        ('Almacen', 'Almacen'),
        ('Entrenador', 'Entrenador'),
        
    ]

    name = models.CharField(max_length=200)
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPES, default='regular')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                           help_text="Discount percentage for this client")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_client_type_display()})"

    @property
    def price_multiplier(self):
        """Returns the price factor based on client type and discount."""
        base_discounts = {
            'regular': 0,
            'Almacen': 5,
            'Distribuidor': 10,
            'Entrenador': 15,
        }
        total_discount = base_discounts.get(self.client_type, 0) + float(self.discount_percent)
        return 1 - (total_discount / 100)
