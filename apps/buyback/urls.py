from django.urls import path
from . import views

urlpatterns = [
    path('', views.buyback_list, name='buyback_list'),
    path('add/', views.buyback_add, name='buyback_add'),
    path('<int:pk>/', views.buyback_detail, name='buyback_detail'),
    path('<int:pk>/receipt/', views.buyback_receipt, name='buyback_receipt'),
    path('<int:pk>/declaration/', views.buyback_declaration, name='buyback_declaration'),
]
