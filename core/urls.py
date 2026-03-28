from django.urls import path
from . import views, admin_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('leads/', views.leads_view, name='leads'),
    path('upload/', views.upload_view, name='upload'),
    
    path('campaigns/', views.campaigns_view, name='campaigns'),
    
    # --- UNIVERSAL EXTRACTION ---
    path('extraction/', views.extraction_upload_view, name='extraction_upload'),
    path('extraction/<int:file_id>/preview/', views.extraction_preview_view, name='extraction_preview'),

    # --- ADMIN PORTAL ---
    path('admin-panel/', admin_views.admin_dashboard_view, name='admin_dashboard'),
]
