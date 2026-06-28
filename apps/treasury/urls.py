from django.urls import path
from . import views

urlpatterns = [
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_form, name='expense_add'),
    path('expenses/<int:pk>/edit/', views.expense_form, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('ledger/', views.treasury_ledger, name='treasury_ledger'),
    path('cash-ledger/', views.cash_ledger, name='cash_ledger'),
    path('bank-ledger/', views.bank_ledger, name='bank_ledger'),
    path('cash/', views.cash_operations, name='cash_operations'),
    path('bank/', views.bank_operations, name='bank_operations'),
]
