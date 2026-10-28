from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Employee, LeaveRequest, LeaveType, Attendance
class DateInput(forms.DateInput): input_type='date'
class LeaveForm(forms.ModelForm):
    class Meta:
        model=LeaveRequest
        fields=['leave_type','start_date','end_date','reason']
        widgets={'start_date':DateInput(),'end_date':DateInput(),'reason':forms.Textarea(attrs={'rows':4})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.fields['leave_type'].queryset=LeaveType.objects.filter(active=True)
class ProfileForm(forms.ModelForm):
    class Meta:
        model=Employee
        fields=['phone','address','emergency_contact']
        widgets={'address':forms.Textarea(attrs={'rows':3})}
class EmployeeForm(forms.ModelForm):
    class Meta:
        model=Employee
        fields=['employee_id','department','job_title','manager','joined_on','phone','address','emergency_contact']
        widgets={'joined_on':DateInput(),'address':forms.Textarea(attrs={'rows':2})}
class AccountCreateForm(UserCreationForm):
    class Meta:
        model=User
        fields=['username','first_name','last_name','email','role']
class AccountEditForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name','email','role','is_active']
class DecisionForm(forms.Form):
    decision=forms.ChoiceField(choices=[('APPROVED','Approve'),('REJECTED','Reject')])
    note=forms.CharField(required=False,max_length=2000,widget=forms.Textarea(attrs={'rows':3}))
class AttendanceEditForm(forms.ModelForm):
    correction_reason=forms.CharField(max_length=300)
    class Meta:
        model=Attendance
        fields=['clock_in','clock_out','note']
        widgets={'clock_in':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M'),'clock_out':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')}
