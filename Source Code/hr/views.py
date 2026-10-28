import csv
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import User, Employee, LeaveRequest, LeaveType, Entitlement, Attendance, AuditEvent, EmailNotification
from .forms import LeaveForm, ProfileForm, EmployeeForm, AccountCreateForm, AccountEditForm, DecisionForm, AttendanceEditForm
from . import services

def hr_required(fn):
    @login_required
    @wraps(fn)
    def wrapped(request,*args,**kwargs):
        if not request.user.is_hr: raise PermissionDenied
        return fn(request,*args,**kwargs)
    return wrapped

def own_employee(user): return get_object_or_404(Employee,user=user)
def visible_leaves(user):
    qs=LeaveRequest.objects.select_related('employee__user','leave_type','approver','decided_by')
    if user.is_hr: return qs
    return qs.filter(Q(employee__user=user)|Q(approver=user)) if user.role==User.Role.MANAGER else qs.filter(employee__user=user)

def errors(request,exc):
    for message in exc.messages: messages.error(request,message)

@login_required
def dashboard(request):
    employee=Employee.objects.filter(user=request.user).first()
    own=LeaveRequest.objects.filter(employee=employee)
    pending=visible_leaves(request.user).filter(status='PENDING').exclude(employee__user=request.user) if request.user.can_review else LeaveRequest.objects.none()
    year=timezone.localdate().year
    balances=[{'type':kind.name,'remaining':services.balance(employee,kind,year)} for kind in LeaveType.objects.filter(active=True)] if employee else []
    return render(request,'hr/dashboard.html',{'employee':employee,'balances':balances,'recent':own.select_related('leave_type')[:5],'pending':pending[:5],'pending_count':pending.count(),'own_pending':own.filter(status='PENDING').count(),'employee_count':Employee.objects.filter(user__is_active=True).count() if request.user.is_hr else None,'open_attendance':Attendance.objects.filter(employee=employee,clock_out__isnull=True).first(),'year':year})

@login_required
def profile(request):
    employee=own_employee(request.user)
    form=ProfileForm(request.POST or None,instance=employee)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            form.save();services.audit(request.user,'Profile updated',employee)
        messages.success(request,'Your contact details have been updated.');return redirect('profile')
    return render(request,'hr/profile.html',{'employee':employee,'form':form})

@login_required
def leaves(request):
    qs=visible_leaves(request.user)
    status=request.GET.get('status','');scope=request.GET.get('scope','mine')
    if scope=='review' and request.user.can_review: qs=qs.exclude(employee__user=request.user)
    elif scope!='all' or not request.user.is_hr: qs=qs.filter(employee__user=request.user)
    if status in LeaveRequest.Status.values: qs=qs.filter(status=status)
    return render(request,'hr/leaves.html',{'leaves':qs[:200],'statuses':LeaveRequest.Status.choices,'selected_status':status,'scope':scope})

@login_required
def leave_new(request):
    own_employee(request.user)
    form=LeaveForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: leave=services.submit_leave(request.user,form.cleaned_data)
        except ValidationError as exc: form.add_error(None,exc)
        else:
            messages.success(request,'Leave submitted. Your approver’s email notification has been queued.');return redirect('leave_detail',pk=leave.pk)
    return render(request,'hr/form.html',{'form':form,'title':'Request time off','eyebrow':'LEAVE MANAGEMENT','description':'Whole working days only. Pending requests reserve your balance. Split requests at the end of the calendar year.','button':'Submit request'})

@login_required
def leave_detail(request,pk):
    leave=get_object_or_404(visible_leaves(request.user),pk=pk)
    can_review=services.may_review(request.user,leave) and leave.status=='PENDING'
    form=DecisionForm(request.POST or None)
    if request.method=='POST':
        if not can_review: raise PermissionDenied
        if form.is_valid():
            try: services.decide_leave(request.user,pk,form.cleaned_data['decision'],form.cleaned_data['note'])
            except ValidationError as exc: form.add_error(None,exc)
            else: messages.success(request,'Decision saved. The employee’s notification has been queued.');return redirect('leave_detail',pk=pk)
    return render(request,'hr/leave_detail.html',{'leave':leave,'form':form,'can_review':can_review})

@login_required
@require_POST
def leave_cancel(request,pk):
    get_object_or_404(LeaveRequest,pk=pk,employee__user=request.user)
    try: services.cancel_leave(request.user,pk)
    except ValidationError as exc: errors(request,exc)
    else: messages.success(request,'Request cancelled and reserved days released.')
    return redirect('leave_detail',pk=pk)

@login_required
def attendance(request):
    qs=Attendance.objects.select_related('employee__user')
    scope=request.GET.get('scope','mine')
    if scope=='team' and request.user.is_hr: pass
    elif scope=='team' and request.user.role==User.Role.MANAGER: qs=qs.filter(employee__manager=request.user)
    else: qs=qs.filter(employee__user=request.user)
    return render(request,'hr/attendance.html',{'records':qs[:200],'scope':scope,'employee':Employee.objects.filter(user=request.user).first()})

@login_required
@require_POST
def attendance_clock(request):
    own_employee(request.user)
    try: services.clock(request.user,request.POST.get('action'))
    except ValidationError as exc: errors(request,exc)
    else: messages.success(request,'Attendance recorded.')
    return redirect('attendance')

@hr_required
def attendance_edit(request,pk):
    record=get_object_or_404(Attendance,pk=pk)
    form=AttendanceEditForm(request.POST or None,instance=record)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            form.save();services.audit(request.user,'Attendance corrected',f'Attendance #{pk}',form.cleaned_data['correction_reason'])
        messages.success(request,'Attendance corrected.');return redirect('attendance')
    return render(request,'hr/form.html',{'form':form,'title':'Correct attendance','description':str(record.employee),'button':'Save correction'})

@hr_required
def employees(request):
    qs=Employee.objects.select_related('user','department','manager')
    q=request.GET.get('q','').strip()
    if q: qs=qs.filter(Q(user__first_name__icontains=q)|Q(user__last_name__icontains=q)|Q(employee_id__icontains=q)|Q(user__email__icontains=q))
    return render(request,'hr/employees.html',{'employees':qs.order_by('employee_id')[:200],'q':q})

@hr_required
def employee_edit(request,pk=None):
    employee=get_object_or_404(Employee,pk=pk) if pk else None
    # Superuser accounts cannot be edited through the HR portal.
    if employee and employee.user.is_superuser: raise PermissionDenied
    account=AccountEditForm(request.POST or None,instance=employee.user,prefix='account') if employee else AccountCreateForm(request.POST or None,prefix='account')
    form=EmployeeForm(request.POST or None,instance=employee,prefix='employee')
    if request.method=='POST' and account.is_valid() and form.is_valid():
        if employee and employee.user_id==request.user.pk and (account.cleaned_data['role']!=request.user.role or not account.cleaned_data['is_active']):
            account.add_error(None,'You cannot deactivate or change your own role.')
        elif form.cleaned_data.get('manager') and employee and form.cleaned_data['manager'].pk==employee.user_id:
            form.add_error('manager','An employee cannot manage themselves.')
        else:
            with transaction.atomic():
                user=account.save();obj=form.save(commit=False);obj.user=user;obj.full_clean();obj.save()
                services.audit(request.user,'Employee updated' if employee else 'Employee created',obj)
            messages.success(request,'Employee account saved.');return redirect('employees')
    return render(request,'hr/employee_form.html',{'account':account,'form':form,'title':'Edit employee' if employee else 'Add employee'})

@hr_required
def operations(request):
    return render(request,'hr/operations.html',{'events':AuditEvent.objects.select_related('actor')[:50],'queued':EmailNotification.objects.filter(sent_at__isnull=True).count(),'failed':EmailNotification.objects.filter(sent_at__isnull=True,attempts__gt=0).count()})

@hr_required
def export_attendance(request):
    response=HttpResponse(content_type='text/csv');response['Content-Disposition']='attachment; filename="attendance.csv"'
    writer=csv.writer(response);writer.writerow(['Employee ID','Employee','Date','Clock in','Clock out','Hours'])
    def safe(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
    for r in Attendance.objects.select_related('employee__user').iterator():
        writer.writerow([safe(r.employee.employee_id),safe(r.employee.user),r.date,timezone.localtime(r.clock_in).isoformat(),timezone.localtime(r.clock_out).isoformat() if r.clock_out else '',r.hours or ''])
    return response
