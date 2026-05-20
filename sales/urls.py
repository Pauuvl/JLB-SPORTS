from django.urls import path
from . import views

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('new/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/cancel/', views.sale_cancel, name='sale_cancel'),
    path('api/product-price/', views.get_product_price, name='product_price_api'),
]
