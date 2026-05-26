from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', lambda request: redirect('dashboard'), name='home'),
    path('dashboard/', include('inventory.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('clients/', include('clients.urls')),
    path('orders/', include('orders.urls')),
    path('quotes/', include('quotes.urls')),
    path('pricing/', include('pricing.urls')),
]
