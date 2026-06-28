from django.urls import path
from . import views

urlpatterns = [
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/add/', views.warehouse_form, name='warehouse_add'),
    path('warehouses/<int:pk>/edit/', views.warehouse_form, name='warehouse_edit'),
    path('warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_form, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_form, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('companies/', views.company_list, name='company_list'),
    path('companies/add/', views.company_form, name='company_add'),
    path('companies/<int:pk>/edit/', views.company_form, name='company_edit'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_form, name='product_add'),
    path('products/<int:pk>/edit/', views.product_form, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/label/', views.product_label_print, name='product_label_print'),
    path('opening-stock/', views.opening_stock, name='opening_stock'),
    path('stock-report/', views.stock_report, name='stock_report'),
    path('warranty-report/', views.warranty_report, name='warranty_report'),
    path('expiry-report/', views.warranty_report, name='expiry_report'),
    path('stock-valuation/', views.stock_valuation, name='stock_valuation'),
]
