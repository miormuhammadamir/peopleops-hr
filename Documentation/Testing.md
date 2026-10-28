# Testing and acceptance

From `Source Code`:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
```

Actual verification in the build environment: Python 3.12, Django 5.2.18, SQLite; 25 tests passed. Tests cover submission and reservation, holidays/weekends, overlap, invalid/cross-year dates, insufficient/unlimited balance, missing/inactive approvers, approval idempotency, rejection and cancellation recredit, HR override, self/unrelated approval denial, balance revalidation, duplicate and overnight attendance, leave-day attendance blocking, notification success/retry/idempotency, employee/manager permissions, protected profile fields, CSRF and POST-only actions, page rendering, onboarding, authentication pages and CSV formula escaping.

These tests do not establish production PostgreSQL concurrency or actual SMTP delivery. Repeat the suite against an isolated PostgreSQL test database (the configured DB user needs permission to create a test database). Test simultaneous leave submissions/decisions under your hosting environment. Do not point tests at production infrastructure. External SMTP is mocked/in-memory in automated tests.

## Manual acceptance before launch

1. Create HR, manager, employee, and unrelated manager accounts. Verify employee/manager cannot open employee administration, policy, operations or CSV endpoints.
2. Configure holidays, workweek and current-year entitlements. Verify inclusive working-day counts, pending reservations and remaining days for your actual policies.
3. Submit from the employee portal. Verify SMTP email reaches the assigned manager and the link uses the public HTTPS host. Approval requires login as an authorized account.
4. Approve/reject from the manager portal; verify the employee's status, balance and decision email. Try unrelated account and self approval.
5. Cancel a pending request; verify balance and notification. Confirm approved/rejected decisions cannot be repeated.
6. Clock in/out, attempt duplicates, test an overnight shift and HR correction. Inspect local timezone and exported timestamps.
7. Change contact details, change password, request a reset and deactivate a test account. Confirm deactivated users cannot continue using the portal.
8. Stop SMTP temporarily and verify queued retry behavior. Restore it, retry, and inspect Ops counts. Validate actual bounce monitoring separately.
9. Test narrow mobile and desktop layouts, backup restoration, TLS/proxy settings, static assets and login rate limits.

No real email was sent during the build. Production hardening, company policy validation, and acceptance are deployment tasks.
