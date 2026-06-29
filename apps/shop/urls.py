from django.urls import path
from . import views
from . import report_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reports/daily/', report_views.daily_report, name='daily_report'),
    path('reports/activity-log/', report_views.activity_log, name='activity_log'),
]
