from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'total_amount', 'status', 'created_at']
    list_filter = ['status']
    inlines = [SaleItemInline]
