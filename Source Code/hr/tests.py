from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.core import mail
from django.utils import timezone
from .models import User, Employee, LeaveType, Entitlement, LeaveRequest, Attendance, EmailNotification, Holiday, AuditEvent
from . import services

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class HRTests(TestCase):
    def setUp(self):
        self.manager=User.objects.create_user('manager','manager@example.com','SafePassphrase!392',role='MANAGER')
        self.hr=User.objects.create_user('hr','hr@example.com','SafePassphrase!392',role='HR')
        self.user=User.objects.create_user('employee','employee@example.com','SafePassphrase!392')
        self.other=User.objects.create_user('other','other@example.com','SafePassphrase!392',role='MANAGER')
        self.employee=Employee.objects.create(user=self.user,employee_id='EMP1',job_title='Executive',joined_on=date(2020,1,1),manager=self.manager)
        self.kind=LeaveType.objects.create(name='Annual')
        self.cap=Entitlement.objects.create(employee=self.employee,leave_type=self.kind,year=2027,days=14)
        self.data={'leave_type':self.kind,'start_date':date(2027,1,4),'end_date':date(2027,1,6),'reason':'Personal time'}
    def leave(self): return services.submit_leave(self.user,self.data)
    def test_submission_reserves_and_queues(self):
        leave=self.leave();self.assertEqual(leave.days,3);self.assertEqual(services.balance(self.employee,self.kind,2027),11)
        self.assertEqual(EmailNotification.objects.get().recipient,self.manager.email)
        self.assertEqual(AuditEvent.objects.count(),1)
    def test_holidays_and_weekends(self):
        Holiday.objects.create(date=date(2027,1,4),name='Holiday')
        self.assertEqual(services.business_days(date(2027,1,2),date(2027,1,5)),1)
    def test_overlap(self):
        self.leave()
        with self.assertRaises(ValidationError): self.leave()
    def test_invalid_date_range(self):
        for start,end in [(date(2027,1,7),date(2027,1,6)),(date(2027,12,31),date(2028,1,3)),(date(2027,1,2),date(2027,1,3))]:
            with self.assertRaises(ValidationError): services.submit_leave(self.user,{**self.data,'start_date':start,'end_date':end})
    def test_insufficient_balance(self):
        self.cap.days=2;self.cap.save()
        with self.assertRaises(ValidationError): self.leave()
    def test_unlimited_type(self):
        self.kind.limited=False;self.kind.save();self.cap.delete()
        self.leave();self.assertIsNone(services.balance(self.employee,self.kind,2027))
    def test_missing_or_invalid_manager(self):
        self.employee.manager=None;self.employee.save()
        with self.assertRaises(ValidationError): self.leave()
        self.employee.manager=self.other;self.employee.save();self.other.is_active=False;self.other.save()
        with self.assertRaises(ValidationError): self.leave()
    def test_approval_and_repeat_decision(self):
        leave=self.leave();services.decide_leave(self.manager,leave.pk,'APPROVED','Enjoy your break')
        leave.refresh_from_db();self.assertEqual(leave.status,'APPROVED');self.assertEqual(leave.decided_by,self.manager)
        self.assertEqual(services.balance(self.employee,self.kind,2027),11)
        with self.assertRaises(ValidationError): services.decide_leave(self.manager,leave.pk,'REJECTED','Again')
    def test_rejection_releases_balance(self):
        leave=self.leave()
        with self.assertRaises(ValidationError): services.decide_leave(self.manager,leave.pk,'REJECTED','')
        services.decide_leave(self.manager,leave.pk,'REJECTED','Team coverage')
        self.assertEqual(services.balance(self.employee,self.kind,2027),14)
    def test_unauthorized_and_self_approval(self):
        leave=self.leave()
        for user in [self.other,self.user]:
            with self.assertRaises(PermissionDenied): services.decide_leave(user,leave.pk,'APPROVED','')
        self.user.role='HR';self.user.save()
        with self.assertRaises(PermissionDenied): services.decide_leave(self.user,leave.pk,'APPROVED','')
    def test_hr_override(self):
        leave=self.leave();services.decide_leave(self.hr,leave.pk,'APPROVED','HR override')
        self.assertEqual(LeaveRequest.objects.get().decided_by,self.hr)
    def test_cancellation(self):
        leave=self.leave();services.cancel_leave(self.user,leave.pk)
        self.assertEqual(services.balance(self.employee,self.kind,2027),14)
        with self.assertRaises(ValidationError): services.cancel_leave(self.user,leave.pk)
    def test_balance_revalidated_on_approval(self):
        leave=self.leave();self.cap.days=1;self.cap.save()
        with self.assertRaises(ValidationError): services.decide_leave(self.manager,leave.pk,'APPROVED','')
    def test_attendance(self):
        services.clock(self.user,'in')
        with self.assertRaises(ValidationError): services.clock(self.user,'in')
        services.clock(self.user,'out');self.assertIsNotNone(Attendance.objects.get().clock_out)
        with self.assertRaises(ValidationError): services.clock(self.user,'out')
        with self.assertRaises(ValidationError): services.clock(self.user,'in')
    def test_overnight_clockout(self):
        now=timezone.now()
        record=Attendance.objects.create(employee=self.employee,date=timezone.localdate()-timedelta(days=1),clock_in=now-timedelta(hours=10))
        services.clock(self.user,'out');record.refresh_from_db();self.assertIsNotNone(record.clock_out)
    def test_notification_delivery(self):
        self.leave();call_command('send_notifications',stdout=StringIO())
        self.assertEqual(len(mail.outbox),1);self.assertIsNotNone(EmailNotification.objects.get().sent_at)
        call_command('send_notifications',stdout=StringIO());self.assertEqual(len(mail.outbox),1)
    def test_notification_retry(self):
        self.leave()
        with patch('hr.management.commands.send_notifications.send_mail',side_effect=RuntimeError('private smtp detail')):
            call_command('send_notifications',stdout=StringIO(),stderr=StringIO())
        item=EmailNotification.objects.get();self.assertEqual(item.attempts,1);self.assertIsNone(item.sent_at);self.assertNotIn('private',item.last_error)
        call_command('send_notifications',stdout=StringIO());item.refresh_from_db();self.assertIsNotNone(item.sent_at)
    def test_employee_access_boundaries(self):
        leave=self.leave();self.client.force_login(self.user)
        for path in ['/employees/','/operations/','/attendance/export/','/employees/new/']:
            self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/leaves/{leave.pk}/').status_code,404)
    def test_profile_cannot_change_role(self):
        self.client.force_login(self.user)
        response=self.client.post('/profile/',{'phone':'123','address':'Test','emergency_contact':'Family','role':'HR','employee_id':'HACK'})
        self.assertEqual(response.status_code,302);self.user.refresh_from_db();self.employee.refresh_from_db()
        self.assertEqual(self.user.role,'EMPLOYEE');self.assertEqual(self.employee.employee_id,'EMP1')
    def test_csrf_and_get_cannot_mutate(self):
        self.client.force_login(self.user);self.assertEqual(self.client.get('/attendance/clock/').status_code,405)
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post('/attendance/clock/',{'action':'in'}).status_code,403)
    def test_portal_pages_render_for_each_role(self):
        leave=self.leave()
        for user,paths in [(self.user,['/','/profile/','/leaves/','/leaves/new/','/attendance/',f'/leaves/{leave.pk}/']), (self.manager,['/','/leaves/?scope=review','/attendance/?scope=team',f'/leaves/{leave.pk}/']), (self.hr,['/','/employees/','/employees/new/','/operations/','/policies/','/policies/hr/entitlement/','/attendance/export/'])]:
            self.client.force_login(user)
            for path in paths:
                with self.subTest(user=user.username,path=path): self.assertEqual(self.client.get(path).status_code,200)
    def test_hr_creates_employee(self):
        self.client.force_login(self.hr)
        response=self.client.post('/employees/new/',{'account-username':'newperson','account-first_name':'New','account-last_name':'Person','account-email':'new@example.com','account-role':'EMPLOYEE','account-password1':'UniquePassphrase!9248','account-password2':'UniquePassphrase!9248','employee-employee_id':'NEW1','employee-job_title':'Analyst','employee-manager':self.manager.pk,'employee-joined_on':'2026-01-01'})
        self.assertEqual(response.status_code,302);self.assertTrue(Employee.objects.filter(employee_id='NEW1').exists())
    def test_login_and_password_pages(self):
        for path in ['/accounts/login/','/accounts/password_reset/']:
            self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.post('/accounts/login/',{'username':'employee','password':'SafePassphrase!392'}).status_code,302)
        self.assertEqual(self.client.get('/accounts/password_change/').status_code,200)
    def test_approved_leave_blocks_clock_in(self):
        today=timezone.localdate()
        LeaveRequest.objects.create(employee=self.employee,leave_type=self.kind,approver=self.manager,start_date=today,end_date=today,days=1,reason='Leave',status='APPROVED')
        with self.assertRaises(ValidationError): services.clock(self.user,'in')
    def test_csv_formula_escape(self):
        self.user.first_name='=SUM(1,1)';self.user.save();services.clock(self.user,'in');self.client.force_login(self.hr)
        response=self.client.get('/attendance/export/')
        self.assertIn("'=SUM(1,1)",response.content.decode())
