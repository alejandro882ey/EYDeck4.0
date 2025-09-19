from django.urls import path
from . import views

app_name = 'cobranzas'

urlpatterns = [
    path('upload/', views.upload_cobranzas, name='upload'),
    path('status/', views.get_cobranzas_status, name='status'),
    path('clear/', views.clear_cobranzas, name='clear'),
    path('preview/', views.preview_cobranzas, name='preview'),
    path('preview_data/', views.preview_cobranzas_data, name='preview_data'),
]
