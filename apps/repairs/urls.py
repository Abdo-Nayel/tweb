from django.urls import path
from . import views

urlpatterns = [
    path('', views.repair_list, name='repair_list'),
    path('add/', views.repair_add, name='repair_add'),
    path('<int:pk>/', views.repair_detail, name='repair_detail'),
    path('<int:pk>/complete/', views.repair_complete, name='repair_complete'),
    path('<int:pk>/status/', views.repair_status, name='repair_status'),
]
