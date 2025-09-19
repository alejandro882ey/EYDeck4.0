from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('status/', views.status_view, name='status'),
    path('clear/', views.clear_view, name='clear'),
]
