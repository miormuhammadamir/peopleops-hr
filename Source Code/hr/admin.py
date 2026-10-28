from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import Department, Holiday, LeaveType, Entitlement, AuditEvent, EmailNotification
from .services import audit
class HRAdminSite(AdminSite):
    site_header='PeopleOps · Policy administration'
    site_title='PeopleOps'
    index_title='Policy & configuration'
    def has_permission(self,request): return request.user.is_active and request.user.is_hr
site=HRAdminSite(name='policy_admin')
class PolicyAdmin(admin.ModelAdmin):
    def has_module_permission(self,request): return request.user.is_hr
    def has_view_permission(self,request,obj=None): return request.user.is_hr
    def has_add_permission(self,request): return request.user.is_hr
    def has_change_permission(self,request,obj=None): return request.user.is_hr
    def has_delete_permission(self,request,obj=None): return False
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        audit(request.user,'Policy updated' if change else 'Policy created',f'{obj._meta.label} #{obj.pk}',str(form.changed_data))
@admin.register(Department,site=site)
class DepartmentAdmin(PolicyAdmin): search_fields=['name']
@admin.register(LeaveType,site=site)
class LeaveTypeAdmin(PolicyAdmin): list_display=['name','limited','active']
@admin.register(Holiday,site=site)
class HolidayAdmin(PolicyAdmin): list_display=['date','name'];ordering=['date']
@admin.register(Entitlement,site=site)
class EntitlementAdmin(PolicyAdmin):
    list_display=['employee','leave_type','year','days']
    list_filter=['year','leave_type']
    search_fields=['employee__employee_id','employee__user__first_name']
    def get_readonly_fields(self,request,obj=None): return ['employee','leave_type','year'] if obj else []
