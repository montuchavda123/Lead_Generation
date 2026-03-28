"""
Business logic services for ConvertOS.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from core.models import Lead, Campaign, FollowUp

logger = logging.getLogger(__name__)


def segment_leads(user):
    """
    Auto-classify leads by age:
      0-7 days  → Hot
      7-30 days → Warm
      30+ days  → Cold
    Skips already-converted leads.
    Returns counts dict.
    """
    now = timezone.now()
    # Filter leads that don't have a conversion record
    leads = Lead.objects.filter(user=user, conversion__isnull=True)

    hot_cutoff = now - timedelta(days=7)
    warm_cutoff = now - timedelta(days=30)

    hot = leads.filter(created_at__gte=hot_cutoff).update(status='hot')
    warm = leads.filter(created_at__lt=hot_cutoff, created_at__gte=warm_cutoff).update(status='warm')
    cold = leads.filter(created_at__lt=warm_cutoff).update(status='cold')

    return {'hot': hot, 'warm': warm, 'cold': cold}


def trigger_campaign(campaign):
    """
    Send campaign message to all leads in the target segment.
    """
    leads = Lead.objects.filter(
        user=campaign.user,
        status=campaign.segment,
    )

    count = 0
    for lead in leads:
        logger.info(
            f"[CAMPAIGN:{campaign.name}] Sending to {lead.name} ({lead.phone}): "
            f"{campaign.message[:50]}..."
        )
        lead.last_contacted = timezone.now()
        lead.save(update_fields=['last_contacted'])
        count += 1

    campaign.sent = True
    campaign.sent_count = count
    campaign.save(update_fields=['sent', 'sent_count'])

    return count


def schedule_followup(lead, hours, message):
    """
    Schedule a follow-up message for a lead after X hours.
    """
    scheduled_at = timezone.now() + timedelta(hours=hours)
    followup = FollowUp.objects.create(
        lead=lead,
        message=message,
        scheduled_at=scheduled_at,
    )
    return followup


def process_pending_followups():
    """
    Process all pending follow-ups that are due.
    """
    now = timezone.now()
    pending = FollowUp.objects.filter(sent=False, scheduled_at__lte=now)

    count = 0
    for followup in pending:
        logger.info(
            f"[FOLLOWUP] Sending to {followup.lead.name}: {followup.message[:50]}..."
        )
        followup.sent = True
        followup.sent_at = now
        followup.save(update_fields=['sent', 'sent_at'])

        followup.lead.last_contacted = now
        followup.lead.save(update_fields=['last_contacted'])
        count += 1

    return count
