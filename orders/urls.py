from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.order_list,    name='order_list'),
    path('new/',                views.order_create,  name='order_create'),
    path('<int:pk>/',           views.order_detail,  name='order_detail'),
    path('<int:pk>/confirm/',   views.order_confirm, name='order_confirm'),
    path('<int:pk>/to-sale/',   views.order_to_sale, name='order_to_sale'),
    path('<int:pk>/delete/',    views.order_delete,  name='order_delete'),
    path('<int:pk>/cancel/',    views.order_cancel,  name='order_cancel'),
]
