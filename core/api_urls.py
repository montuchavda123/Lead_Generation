"""ConvertOS API URL routing."""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    # ── Auth ─────────────────────────────────────────
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='api-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api-refresh'),

    # ── Leads ────────────────────────────────────────
    path('leads/', api_views.LeadListAPIView.as_view(), name='api-leads'),
    path('leads/upload/', api_views.LeadUploadAPIView.as_view(), name='api-leads-upload'),
    path('leads/segment/', api_views.SegmentLeadsAPIView.as_view(), name='api-leads-segment'),
    path('leads/<int:lead_id>/convert/', api_views.ConvertLeadAPIView.as_view(), name='api-lead-convert'),

    # ── Dashboard ────────────────────────────────────
    path('dashboard/', api_views.DashboardAPIView.as_view(), name='api-dashboard'),

    # ── Campaigns & Follow-ups ───────────────────────
    path('campaigns/', api_views.CampaignListAPIView.as_view(), name='api-campaigns'),
    path('campaigns/<int:campaign_id>/trigger/', api_views.TriggerCampaignAPIView.as_view(), name='api-campaign-trigger'),
    path('followups/schedule/', api_views.ScheduleFollowUpAPIView.as_view(), name='api-followup-schedule'),

    # ── Universal Extraction ─────────────────────────
    path('extraction/upload/', api_views.ExtractionUploadAPIView.as_view(), name='api-extraction-upload'),
    path('extraction/status/<int:file_id>/', api_views.ExtractionStatusAPIView.as_view(), name='api-extraction-status'),
    path('extraction/download/excel/', api_views.ExtractionDownloadExcelAPIView.as_view(), name='api-extraction-download-excel'),
    path('extraction/download/csv/', api_views.ExtractionDownloadCSVAPIView.as_view(), name='api-extraction-download-csv'),
]
