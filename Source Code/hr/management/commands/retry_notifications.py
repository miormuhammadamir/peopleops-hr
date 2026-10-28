from django.core.management.base import BaseCommand
from hr.models import EmailNotification
class Command(BaseCommand):
    help='Reset failed notification attempts after fixing SMTP configuration.'
    def handle(self,*args,**kwargs):
        n=EmailNotification.objects.filter(sent_at__isnull=True,attempts__gt=0).update(attempts=0,last_error='')
        self.stdout.write(f'Reset {n} notification(s).')
