from django.contrib import admin
from .models import Product, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'talla',
        'sale_price',
        'stock_quantity',
        'is_low_stock'
    ]

    list_filter = [
        'category',
        'talla'
    ]

    search_fields = [
        'name'
    ]