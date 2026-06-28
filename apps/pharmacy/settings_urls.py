from django.urls import path
from django.views.generic import RedirectView
from . import settings_views

urlpatterns = [
    path('', settings_views.settings_home, name='settings_home'),
    path('shop/', settings_views.shop_profile_form, name='shop_profile'),
    path('pharmacy/', RedirectView.as_view(pattern_name='shop_profile', permanent=True)),
    path('branches/', RedirectView.as_view(pattern_name='settings_home', permanent=False)),
    path('branches/add/', RedirectView.as_view(pattern_name='settings_home', permanent=False)),
    path('branches/<int:pk>/edit/', RedirectView.as_view(pattern_name='settings_home', permanent=False)),
    path('branches/<int:pk>/delete/', RedirectView.as_view(pattern_name='settings_home', permanent=False)),
    path('banks/', settings_views.bank_list, name='bank_list'),
    path('banks/add/', settings_views.bank_form, name='bank_add'),
    path('banks/<int:pk>/edit/', settings_views.bank_form, name='bank_edit'),
    path('banks/<int:pk>/delete/', settings_views.bank_delete, name='bank_delete'),
    path('users/', settings_views.user_list, name='user_list'),
    path('users/add/', settings_views.user_form, name='user_add'),
    path('users/<int:pk>/edit/', settings_views.user_form, name='user_edit'),
    path('users/<int:pk>/delete/', settings_views.user_delete, name='user_delete'),
    path('barcode/', settings_views.barcode_settings, name='barcode_settings'),
    path('receipt/', settings_views.receipt_settings, name='receipt_settings'),
    path('telegram/', settings_views.telegram_settings, name='telegram_settings'),
]
