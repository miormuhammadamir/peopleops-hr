from django.urls import path, include
from hr import views
from hr.admin import site
urlpatterns=[
 path('policies/',site.urls),path('accounts/',include('django.contrib.auth.urls')),
 path('',views.dashboard,name='dashboard'),path('profile/',views.profile,name='profile'),
 path('leaves/',views.leaves,name='leaves'),path('leaves/new/',views.leave_new,name='leave_new'),
 path('leaves/<int:pk>/',views.leave_detail,name='leave_detail'),path('leaves/<int:pk>/cancel/',views.leave_cancel,name='leave_cancel'),
 path('attendance/',views.attendance,name='attendance'),path('attendance/clock/',views.attendance_clock,name='attendance_clock'),path('attendance/<int:pk>/edit/',views.attendance_edit,name='attendance_edit'),path('attendance/export/',views.export_attendance,name='export_attendance'),
 path('employees/',views.employees,name='employees'),path('employees/new/',views.employee_edit,name='employee_new'),path('employees/<int:pk>/edit/',views.employee_edit,name='employee_edit'),path('operations/',views.operations,name='operations'),
]
