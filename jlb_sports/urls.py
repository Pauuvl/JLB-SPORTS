from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('dashboard'), name='home'),
    path('dashboard/', include('inventory.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('clients/', include('clients.urls')),
    path('orders/', include('orders.urls')),
    path('quotes/', include('quotes.urls')),
    path('pricing/', include('pricing.urls')),
]
