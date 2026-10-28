from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import User, Employee, LeaveRequest, Holiday, Entitlement, AuditEvent, EmailNotification, Attendance

def business_days(start,end):
    holidays=set(Holiday.objects.filter(date__range=(start,end)).values_list('date',flat=True))
    return sum((start+timedelta(days=i)).weekday() in settings.WORKING_WEEKDAYS and start+timedelta(days=i) not in holidays for i in range((end-start).days+1))

def used_days(employee,leave_type,year,exclude=None):
    qs=LeaveRequest.objects.filter(employee=employee,leave_type=leave_type,start_date__year=year,status__in=['PENDING','APPROVED'])
    if exclude: qs=qs.exclude(pk=exclude)
    return qs.aggregate(n=Sum('days'))['n'] or 0

def balance(employee,leave_type,year):
    if not leave_type.limited: return None
    cap=Entitlement.objects.filter(employee=employee,leave_type=leave_type,year=year).values_list('days',flat=True).first() or 0
    return cap-used_days(employee,leave_type,year)

def audit(actor,action,target,detail=''):
    AuditEvent.objects.create(actor=actor,action=action,target=str(target),detail=detail)

def notify(user,subject,body):
    EmailNotification.objects.create(recipient=user.email,subject=subject,body=body)

@transaction.atomic
def submit_leave(user,data):
    employee=Employee.objects.select_for_update().get(user=user)
    start,end=data['start_date'],data['end_date']; kind=data['leave_type']
    if end<start: raise ValidationError('End date must follow start date.')
    if start.year!=end.year: raise ValidationError('Split requests across calendar years.')
    if (end-start).days>366: raise ValidationError('The request is too long.')
    if not kind.active: raise ValidationError('This leave type is inactive.')
    if start<employee.joined_on: raise ValidationError('Leave cannot precede the employment start date.')
    days=business_days(start,end)
    if not days: raise ValidationError('Choose at least one working day.')
    if LeaveRequest.objects.filter(employee=employee,status__in=['PENDING','APPROVED'],start_date__lte=end,end_date__gte=start).exists(): raise ValidationError('These dates overlap an existing request.')
    remaining=balance(employee,kind,start.year)
    if remaining is not None and days>remaining: raise ValidationError(f'Insufficient balance. Available: {remaining} days.')
    manager=employee.manager
    if not manager or not manager.is_active or not manager.can_review or manager.pk==user.pk: raise ValidationError('HR must assign an active approver to your employee profile.')
    leave=LeaveRequest.objects.create(employee=employee,approver=manager,days=days,**data)
    audit(user,'Leave submitted',leave)
    notify(manager,f'Leave request #{leave.pk} needs approval',f'{user} requested {days} working day(s). Sign in to review:\n{settings.SITE_URL}/leaves/{leave.pk}/')
    return leave

def may_review(user,leave):
    return user.is_active and user.pk!=leave.employee.user_id and (user.is_hr or (user.role==User.Role.MANAGER and leave.approver_id==user.pk))

@transaction.atomic
def decide_leave(user,pk,status,note):
    # Consistent employee-first lock ordering serializes balances and decisions.
    employee_id=LeaveRequest.objects.values_list('employee_id',flat=True).get(pk=pk)
    employee=Employee.objects.select_for_update().get(pk=employee_id)
    leave=LeaveRequest.objects.select_for_update().select_related('employee__user','leave_type').get(pk=pk)
    if not may_review(user,leave): raise PermissionDenied
    if leave.status!='PENDING': raise ValidationError('This request has already been processed.')
    if status not in ['APPROVED','REJECTED']: raise ValidationError('Invalid decision.')
    if status=='REJECTED' and not note.strip(): raise ValidationError('Explain why the request is rejected.')
    if status=='APPROVED':
        remaining=balance(employee,leave.leave_type,leave.start_date.year)
        if remaining is not None and remaining<0: raise ValidationError('Balance changed. Ask HR to review the entitlement.')
    leave.status=status;leave.decision_note=note;leave.decided_by=user;leave.decided_at=timezone.now();leave.save()
    audit(user,'Leave '+status.lower(),leave,note)
    notify(employee.user,f'Leave request #{pk}: {status.lower()}',f'Your leave request is {status.lower()}. Sign in to view the decision:\n{settings.SITE_URL}/leaves/{pk}/')
    return leave

@transaction.atomic
def cancel_leave(user,pk):
    employee=Employee.objects.select_for_update().get(user=user)
    leave=LeaveRequest.objects.select_for_update().get(pk=pk,employee=employee)
    if leave.status!='PENDING': raise ValidationError('Only pending requests can be cancelled. Contact HR for approved leave corrections.')
    leave.status='CANCELLED';leave.save(update_fields=['status'])
    audit(user,'Leave cancelled',leave)
    notify(leave.approver,f'Leave request #{pk} cancelled',f'The employee cancelled this request. {settings.SITE_URL}/leaves/{pk}/')

@transaction.atomic
def clock(user,action):
    employee=Employee.objects.select_for_update().get(user=user)
    now=timezone.now();today=timezone.localdate()
    if action=='in':
        if Attendance.objects.filter(employee=employee,clock_out__isnull=True).exists(): raise ValidationError('You already have an open attendance record. Clock out first.')
        if Attendance.objects.filter(employee=employee,date=today).exists(): raise ValidationError('You already clocked in today.')
        if LeaveRequest.objects.filter(employee=employee,status='APPROVED',start_date__lte=today,end_date__gte=today).exists(): raise ValidationError('You are on approved leave today. Contact HR if this is incorrect.')
        record=Attendance.objects.create(employee=employee,date=today,clock_in=now)
    elif action=='out':
        record=Attendance.objects.select_for_update().filter(employee=employee,clock_out__isnull=True).first()
        if not record: raise ValidationError('No open clock in was found.')
        record.clock_out=now;record.save(update_fields=['clock_out'])
    else: raise ValidationError('Invalid attendance action.')
    audit(user,'Clock '+action,f'Attendance #{record.pk}')
