# PeopleOps — Django HR system

A runnable Django web application with employee, manager, and HR administrator portals. Python 3.10+; Django 5.2.18; SQLite for local evaluation and PostgreSQL for production.

## Quick start

Open a terminal in `Source Code`:

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://127.0.0.1:8000/ and sign in with the superuser you just created. A superuser has HR access even if their displayed role is Employee. No real accounts, databases, credentials, or preset passwords are shipped.

1. Open **Policies & balances**. Add departments, leave types, holidays, and later annual entitlements.
2. Open **Employees**. Add manager accounts first, then employee accounts and their assigned managers. Initial passwords must satisfy Django password validation. Give initial credentials privately; users can change or reset passwords.
3. Create yearly entitlements for capped leave types. Without an entitlement, an employee has zero available days. Set uncapped types (e.g., unpaid leave) to `limited=False`.
4. Sign in as an employee. Check profile, update contact details, clock in/out, and submit leave.
5. Sign in as the assigned manager or HR. Review the request under Approvals.
6. In another terminal, run `python manage.py send_notifications` to deliver queued request/decision emails. Local development prints messages in that terminal. Configure SMTP and schedule this command every minute for actual email.

The administrator account can operate without an employee record. To give an existing superuser their own employee profile, use the Django shell with `Employee.objects.create(...)`; do not duplicate their account. HR portal employee editing intentionally excludes superuser accounts.

## Optional sample data

Local development only; allowances are examples, not statutory or company policy:

```bash
# Linux / macOS: choose your own password, at least 12 characters
export DEMO_PASSWORD='choose-a-long-unique-demo-password'
python manage.py seed_demo
# Windows PowerShell: $env:DEMO_PASSWORD = 'choose-a-long-unique-demo-password'
```

Creates usernames `manager` and `employee`, annual/sick/emergency/unpaid/other leave types and example current-year allowances. The manager's own leave requires HR to assign a different approver. Existing account passwords are never overwritten. Do not use demo data in production.

## Included

- Responsive employee dashboard, profile/contact editing, password change/reset.
- Separate employee, manager, and HR access with object-level leave permissions.
- HR employee onboarding, role assignment, reporting line assignment, account deactivation.
- Server-timestamp attendance, duplicate prevention, overnight clock-out, audited HR corrections and CSV export.
- Annual, sick, emergency, unpaid, and custom leave types; yearly balances and company holidays.
- Pending → approved/rejected/cancelled lifecycle, overlap checking, reserved pending days, decision history.
- Assigned manager email notifications, HR override, logged-in approval pages, no self approval.
- Persistent email outbox, retries, sanitized delivery errors, activity log.
- Migrations, tests, environment example, security/deployment instructions, schema/ERD.

Read `Documentation/Installation.md` for email/deployment, `Documentation/Policies.md` for scope and assumptions, and `Documentation/Testing.md` for validation. This is an implemented application baseline, not a claim of production certification. Configure your policies and infrastructure and perform acceptance testing before live HR use.
