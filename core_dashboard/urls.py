from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_file_view, name='upload_file'),
    path('delete-data-cache/', views.delete_data_and_cache_view, name='delete_data_cache'),
    path('tables/', views.tables_view, name='tables'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('messaging/', views.messaging_view, name='messaging'),
    path('data_downloads/', views.data_downloads_view, name='data_downloads'),
    
    # Module URLs
    path('manager-revenue-days/', include('core_dashboard.modules.manager_revenue_days.urls')),
    path('cobranzas/', include('core_dashboard.modules.cobranzas.urls')),
    path('facturacion/', include('core_dashboard.modules.facturacion.urls')),
]