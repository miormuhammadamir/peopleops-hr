from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from hr.models import EmailNotification
class Command(BaseCommand):
    help='Send up to 100 queued notifications. Schedule every minute; PostgreSQL is recommended.'
    def handle(self,*args,**options):
        ids=list(EmailNotification.objects.filter(sent_at__isnull=True,attempts__lt=10).values_list('pk',flat=True)[:100])
        sent=0
        for pk in ids:
            with transaction.atomic():
                item=EmailNotification.objects.select_for_update().get(pk=pk)
                if item.sent_at or item.attempts>=10: continue
                item.attempts+=1
                try:
                    result=send_mail(item.subject,item.body,settings.DEFAULT_FROM_EMAIL,[item.recipient])
                    if result!=1: raise RuntimeError('Email backend did not accept message')
                except Exception:
                    # Keep transport errors and credentials out of persisted diagnostics.
                    item.last_error='Delivery failed. Check mail service configuration and server logs.'
                    self.stderr.write(f'Notification #{pk} delivery failed.')
                else:
                    item.sent_at=timezone.now();item.last_error='';sent+=1
                item.save(update_fields=['attempts','sent_at','last_error'])
        self.stdout.write(f'Sent {sent} notification(s).')
