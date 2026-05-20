from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'client_type', 'email', 'phone', 'discount_percent']
    list_filter = ['client_type']
    search_fields = ['name', 'email']

