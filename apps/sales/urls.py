from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales_list, name='sales_list'),
    path('add/', views.sales_add, name='sales_add'),
    path('reports/items/', views.sales_items_report, name='sales_items_report'),
    path('reports/profit/', views.sales_profit_report, name='sales_profit_report'),
    path('product-lookup/', views.product_lookup, name='sales_product_lookup'),
    path('customer-lookup/', views.customer_lookup, name='customer_lookup'),
    path('<int:pk>/reopen/', views.sales_reopen, name='sales_reopen'),
    path('<int:pk>/receipt/', views.sales_receipt, name='sales_receipt'),
    path('<int:pk>/pos/add/', views.sales_pos_add, name='sales_pos_add'),
    path('<int:pk>/pos/remove/', views.sales_pos_remove, name='sales_pos_remove'),
    path('<int:pk>/pos/qty/', views.sales_pos_qty, name='sales_pos_qty'),
    path('<int:pk>/edit/', views.sales_form, name='sales_edit'),
    path('<int:pk>/delete/', views.sales_delete, name='sales_delete'),
    path('<int:pk>/', views.sales_detail, name='sales_detail'),
]
