from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, admin_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('leads/', views.leads_view, name='leads'),
    path('upload/', views.upload_view, name='upload'),
    
    path('campaigns/', views.campaigns_view, name='campaigns'),
    
    # --- PASSWORD RESET ---
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    # --- UNIVERSAL EXTRACTION ---
    path('extraction/', views.extraction_upload_view, name='extraction_upload'),
    path('extraction/<int:file_id>/preview/', views.extraction_preview_view, name='extraction_preview'),

    # --- ADMIN PORTAL ---
    path('admin-panel/', admin_views.admin_dashboard_view, name='admin_dashboard'),
]
