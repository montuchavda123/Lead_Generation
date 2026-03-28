"""
Management command to process pending follow-ups.
Usage: python manage.py process_followups
Can be run via cron job or Celery beat in production.
"""
from django.core.management.base import BaseCommand
from core.services import process_pending_followups


class Command(BaseCommand):
    help = 'Process all pending follow-up messages that are due.'

    def handle(self, *args, **options):
        count = process_pending_followups()
        self.stdout.write(
            self.style.SUCCESS(f'Processed {count} follow-up(s).')
        )
