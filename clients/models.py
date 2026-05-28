from django.db import models


class Client(models.Model):
    CLIENT_TYPES = [
        ('regular', 'Regular'),
        ('Distribuidor', 'Distribuidor'),
        ('Almacen', 'Almacen'),
        ('Entrenador', 'Entrenador'),
    ]

    name = models.CharField(max_length=200)
    cedula = models.CharField(max_length=30, blank=True, default='', verbose_name='Cédula / NIT')
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPES, default='regular')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    municipio = models.CharField(max_length=100, blank=True, default='')
    address = models.TextField(blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                           help_text="Descuento base del cliente (%)")
    notes = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_client_type_display()})"

    @property
    def price_multiplier(self):
        total_discount = float(self.discount_percent)
        return 1 - (total_discount / 100)
