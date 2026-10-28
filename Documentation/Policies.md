# Roles, rules, and scope

| Capability | Employee | Manager | HR / superuser |
|---|---|---|---|
| Own profile/contact editing | Yes | Yes | If employee profile exists |
| Own leave/balance/attendance | Yes | Yes | If employee profile exists |
| Review assigned requests | No | Yes | All except self |
| Team attendance | No | Current direct reports | All |
| Edit employee accounts and roles | No | No | Yes, except superusers |
| Correct attendance / export CSV | No | No | Yes |
| Policies, holidays, yearly entitlements | No | No | Yes |
| Audit and email queue counts | No | No | Yes |

Superuser accounts are maintained through the Django CLI/shell, not HR forms. A superuser's effective HR access does not depend on the displayed role. New HR administrators do not require `is_staff`: the restricted policy admin checks the HR role directly. General Django user/group/permission admin pages are not exposed. Ordinary staff/group permissions do not grant HR access.

## Approval workflow

Employees submit a whole-day request to their assigned active manager or HR user. The assigned approver is captured on the request; changing a reporting manager does not silently reassign existing requests. HR can decide any pending request except their own. HR can review all requests through Operations → All leave requests. Managers only see their own and assigned requests; their attendance team scope follows current direct reports. If an assigned approver is deactivated or demoted, HR must process the pending request.

Pending requests reserve days. Approval preserves that reservation as used leave. Rejection/cancellation releases it. Rejection requires a note. Employees can cancel pending requests only. Decisions cannot be edited in the portal. Approved leave reversal/recredit, delegated approvers, multi-level approval chains and reassignment are future extensions; if required, implement an audited workflow before deployment rather than editing database rows casually.

Requests cannot overlap another pending/approved request, even across types. They cannot precede the employment start date. Backdated requests are allowed for sickness and HR reporting; the approval policy should address them. Requests must stay within one calendar year, contain at least one working day, and fit the employee's entitlement. Weekends come from `WORKING_WEEKDAYS` (Monday=0, Sunday=6), with company holidays excluded. No half days, hourly leave, accrual, carry-forward, automatic proration, shift-specific calendars, or statutory entitlement calculations are included. Holidays/working-day policy changes do not recalculate previously submitted day counts; use prospective changes and review pending requests before changing policy.

All leave types are configurable. Sick leave does not currently collect medical certificates or enforce medical documentation. Optional proof uploads would require private storage, upload validation, and access control; no public upload endpoint is provided. Example annual/sick allowances in seed_demo are demonstration values only. HR must configure the company's approved entitlements and holidays each year.

## Attendance

One clock-in record per employee per local calendar date. Server time is authoritative; employees cannot backdate timestamps. Open shifts must close before another clock-in, and can close after midnight. Attendance is blocked on dates covered by approved leave. The app does not check GPS, biometrics, break durations, tardiness, payroll calculations, overtime rules, or scheduled absence. Hours are elapsed time from in to out with no break deduction. HR can correct existing timestamps and notes with a mandatory correction reason; there is no manual attendance creation screen. The activity log records actor, action, record and correction reason. It does not store full before/after values and is not a tamper-evident compliance log.

## Account and personal data

Employees can change only phone, address, and emergency contact. HR owns names, emails, job details, manager, role and activation. Email addresses are unique at database level but uniqueness is case-sensitive under default PostgreSQL collation; normalize organization emails during onboarding. Account deactivation blocks new login and invalidates access on subsequent authenticated requests. HR cannot demote/deactivate themselves through the employee form. Employee records and historical references use PROTECT to discourage deletion.

This project covers the requested core HR workflows. It does not include payroll, recruitment, performance management, expense claims, organization multi-tenancy, public signup, external HR integrations, MFA, advanced search/pagination, or a REST API. Listing screens cap results at 200, activity at 50; attendance export includes all records. Expand reporting before larger-scale rollout. The security posture and actual company rules require deployment and acceptance review.
