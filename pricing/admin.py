from django.contrib import admin
from .models import PriceList, PriceListItem

class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 1

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['name', 'client_type', 'is_active']
    inlines = [PriceListItemInline]
