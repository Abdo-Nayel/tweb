from django.urls import path
from . import views

urlpatterns = [
    path('', views.return_list, name='return_list'),
    path('add/', views.return_add, name='return_add'),
    path('lookup/product/', views.product_lookup, name='return_product_lookup'),
    path('<int:pk>/edit/', views.return_edit, name='return_edit'),
    path('<int:pk>/pos/add/', views.return_pos_add, name='return_pos_add'),
    path('<int:pk>/pos/remove/', views.return_pos_remove, name='return_pos_remove'),
    path('<int:pk>/pos/qty/', views.return_pos_qty, name='return_pos_qty'),
    path('<int:pk>/', views.return_detail, name='return_detail'),
]
