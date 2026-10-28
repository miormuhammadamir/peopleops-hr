from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F

class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE='EMPLOYEE','Employee'
        MANAGER='MANAGER','Manager'
        HR='HR','HR administrator'
    role=models.CharField(max_length=12,choices=Role.choices,default=Role.EMPLOYEE)
    email=models.EmailField(unique=True)
    @property
    def is_hr(self): return self.is_superuser or self.role==self.Role.HR
    @property
    def can_review(self): return self.is_hr or self.role==self.Role.MANAGER
    def __str__(self): return self.get_full_name() or self.username

class Department(models.Model):
    name=models.CharField(max_length=120,unique=True)
    def __str__(self): return self.name

class Employee(models.Model):
    user=models.OneToOneField(User,on_delete=models.PROTECT,related_name='employee')
    employee_id=models.CharField(max_length=30,unique=True)
    department=models.ForeignKey(Department,on_delete=models.PROTECT,null=True,blank=True)
    job_title=models.CharField(max_length=120)
    manager=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='direct_reports',limit_choices_to={'is_active':True,'role__in':['MANAGER','HR']})
    joined_on=models.DateField()
    phone=models.CharField(max_length=30,blank=True)
    address=models.TextField(blank=True)
    emergency_contact=models.CharField(max_length=200,blank=True)
    def clean(self):
        if self.manager_id == self.user_id: raise ValidationError({'manager':'An employee cannot manage themselves.'})
        if self.manager_id and (not self.manager.is_active or not self.manager.can_review): raise ValidationError({'manager':'Choose an active manager or HR administrator.'})
    def __str__(self): return f'{self.employee_id} · {self.user}'

class Holiday(models.Model):
    date=models.DateField(unique=True)
    name=models.CharField(max_length=150)
    def __str__(self): return f'{self.date} {self.name}'

class LeaveType(models.Model):
    name=models.CharField(max_length=80,unique=True)
    limited=models.BooleanField(default=True,help_text='Requires a yearly entitlement. Unlimited types have no balance cap.')
    active=models.BooleanField(default=True)
    def __str__(self): return self.name

class Entitlement(models.Model):
    employee=models.ForeignKey(Employee,on_delete=models.PROTECT)
    leave_type=models.ForeignKey(LeaveType,on_delete=models.PROTECT)
    year=models.PositiveIntegerField()
    days=models.PositiveSmallIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['employee','leave_type','year'],name='unique_entitlement')]
    def __str__(self): return f'{self.employee} / {self.leave_type} / {self.year}'

class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING='PENDING','Pending'
        APPROVED='APPROVED','Approved'
        REJECTED='REJECTED','Rejected'
        CANCELLED='CANCELLED','Cancelled'
    employee=models.ForeignKey(Employee,on_delete=models.PROTECT)
    leave_type=models.ForeignKey(LeaveType,on_delete=models.PROTECT)
    approver=models.ForeignKey(User,on_delete=models.PROTECT,related_name='assigned_leaves')
    start_date=models.DateField()
    end_date=models.DateField()
    days=models.PositiveSmallIntegerField()
    reason=models.TextField(max_length=2000)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.PENDING)
    decision_note=models.TextField(max_length=2000,blank=True)
    decided_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='leave_decisions')
    decided_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['employee','status','start_date'])]
        constraints=[models.CheckConstraint(condition=Q(end_date__gte=F('start_date')),name='leave_dates_valid'),models.CheckConstraint(condition=Q(days__gt=0),name='leave_days_positive')]
    def __str__(self): return f'#{self.pk} {self.employee} · {self.leave_type}'

class Attendance(models.Model):
    employee=models.ForeignKey(Employee,on_delete=models.PROTECT)
    date=models.DateField()
    clock_in=models.DateTimeField()
    clock_out=models.DateTimeField(null=True,blank=True)
    note=models.CharField(max_length=300,blank=True)
    class Meta:
        ordering=['-date','-clock_in']
        constraints=[models.UniqueConstraint(fields=['employee','date'],name='one_attendance_per_day'),models.CheckConstraint(condition=Q(clock_out__isnull=True)|Q(clock_out__gte=F('clock_in')),name='attendance_order')]
    @property
    def hours(self): return round((self.clock_out-self.clock_in).total_seconds()/3600,2) if self.clock_out else None
    def clean(self):
        if self.clock_out and self.clock_out<self.clock_in: raise ValidationError('Clock out must follow clock in.')

class AuditEvent(models.Model):
    actor=models.ForeignKey(User,on_delete=models.PROTECT,null=True)
    action=models.CharField(max_length=80)
    target=models.CharField(max_length=150)
    detail=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']

class EmailNotification(models.Model):
    recipient=models.EmailField()
    subject=models.CharField(max_length=200)
    body=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    sent_at=models.DateTimeField(null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0)
    last_error=models.CharField(max_length=250,blank=True)
    class Meta: ordering=['created_at']
