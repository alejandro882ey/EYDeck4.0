"""
Manager Revenue Days URLs
========================

URL patterns for Manager Revenue Days module.
"""

from django.urls import path
from . import views

app_name = 'manager_revenue_days'

urlpatterns = [
    path('upload/', views.upload_manager_revenue_days, name='upload'),
    path('status/', views.get_manager_revenue_days_status, name='status'),
    path('clear/', views.clear_manager_revenue_days, name='clear'),
]
