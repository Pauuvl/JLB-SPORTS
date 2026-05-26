from django.contrib import admin
from .models import Product, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'codigo',
        'name',
        'category',
        'marca',
        'talla',
        'color',
        'sale_price',
        'stock_quantity',
        'get_is_low_stock',
    ]

    list_filter = [
        'category',
        'talla',
        'marca',
    ]

    search_fields = [
        'name',
        'codigo',
        'color',
        'marca',
    ]

    @admin.display(boolean=True, description='Stock bajo')
    def get_is_low_stock(self, obj):
        return obj.is_low_stock
