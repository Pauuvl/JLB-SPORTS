from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.quote_list,   name='quote_list'),
    path('new/',              views.quote_create, name='quote_create'),
    path('<int:pk>/',         views.quote_detail, name='quote_detail'),
    path('<int:pk>/status/',  views.quote_status, name='quote_status'),
    path('<int:pk>/delete/',  views.quote_delete, name='quote_delete'),
]
