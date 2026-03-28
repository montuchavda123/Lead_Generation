from django.contrib import admin
from .models import Lead, Conversion, Campaign, FollowUp

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'status', 'user', 'last_contacted', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'phone', 'email']

@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ['lead', 'converted', 'revenue', 'converted_at']
    list_filter = ['converted']

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'segment', 'sent', 'sent_count', 'created_at']
    list_filter = ['segment', 'sent']

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['lead', 'scheduled_at', 'sent', 'sent_at']
    list_filter = ['sent']
