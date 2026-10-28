# Web routes

Server-rendered HTML, session cookies and CSRF-protected forms. There is no public JSON/REST API. Unsafe actions require POST. Successful mutations use redirects; anonymous sessions redirect to login; forbidden roles return 403 and invisible records return 404.

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Role-aware dashboard |
| GET/POST | `/accounts/login/` | Authentication |
| POST | `/accounts/logout/` | End session |
| GET/POST | `/accounts/password_change/` | Authenticated password change |
| GET/POST | `/accounts/password_reset/` | Reset request; Django token confirmation routes included |
| GET/POST | `/profile/` | Own contact profile |
| GET | `/leaves/?scope=mine\|review\|all&status=PENDING` | Role-filtered leave lists |
| GET/POST | `/leaves/new/` | Submit own leave |
| GET/POST | `/leaves/<id>/` | View request / authorized approval decision |
| POST | `/leaves/<id>/cancel/` | Cancel own pending request |
| GET | `/attendance/?scope=mine\|team` | Attendance list |
| POST | `/attendance/clock/` | `action=in` or `action=out` |
| GET/POST | `/attendance/<id>/edit/` | HR correction with reason |
| GET | `/attendance/export/` | HR CSV export |
| GET | `/employees/?q=...` | HR employee search |
| GET/POST | `/employees/new/` | HR account and profile creation |
| GET/POST | `/employees/<id>/edit/` | HR account/profile maintenance |
| GET | `/operations/` | HR activity and queue counts |
| GET/POST | `/policies/` | Restricted Django policy administration |
