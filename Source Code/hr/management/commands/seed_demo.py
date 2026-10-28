import os
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from hr.models import User, Employee, Department, LeaveType, Entitlement
class Command(BaseCommand):
    help='Create sample employee and manager accounts locally. Requires DEMO_PASSWORD; no preset password.'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        password=os.getenv('DEMO_PASSWORD')
        if not settings.DEBUG or not password or len(password)<12: raise CommandError('Local DEBUG mode and DEMO_PASSWORD of at least 12 characters are required.')
        department,_=Department.objects.get_or_create(name='Operations')
        manager=None
        for username,first,last,role in [('manager','Amir','Rahman','MANAGER'),('employee','Diya','Ahmad','EMPLOYEE')]:
            user,created=User.objects.get_or_create(username=username,defaults={'email':username+'@example.com','first_name':first,'last_name':last,'role':role})
            if created: user.set_password(password);user.save()
            employee,_=Employee.objects.get_or_create(user=user,defaults={'employee_id':'EMP-001' if role=='MANAGER' else 'EMP-002','department':department,'job_title':'Team manager' if role=='MANAGER' else 'Marketing executive','joined_on':date(date.today().year,1,1),'manager':manager})
            if role=='MANAGER': manager=user
            for name,days,limited in [('Annual leave',14,True),('Sick leave',14,True),('Emergency leave',3,True),('Unpaid leave',0,False),('Other leave',0,False)]:
                kind,_=LeaveType.objects.get_or_create(name=name,defaults={'limited':limited})
                if limited: Entitlement.objects.get_or_create(employee=employee,leave_type=kind,year=date.today().year,defaults={'days':days})
        self.stdout.write('Sample accounts created (existing passwords unchanged). Allowances are demonstration values only.')
