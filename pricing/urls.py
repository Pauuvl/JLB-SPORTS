from django.urls import path
from . import views

urlpatterns = [
    path('', views.pricing_overview, name='pricing_overview'),
    path('new/', views.price_list_create, name='price_list_create'),
    path('<int:pk>/', views.price_list_detail, name='price_list_detail'),
    path('<int:pk>/add-item/', views.add_price_list_item, name='add_price_list_item'),
]
