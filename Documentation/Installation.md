# Installation and operations

## Runtime and database

Use the quick start in README. Install Python 3.10 or later (tested with Python 3.12). Dependencies are in `Source Code/requirements.txt`. No JavaScript build step or external CSS framework is needed. The optional Google Fonts import has system-font fallbacks.

The `.env.example` file is documentation, not an automatic configuration loader. Set environment variables using your operating system or service manager. Never commit an actual `.env` or database. Use PostgreSQL for production. Set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` before running migrations. Transactions lock employee rows to serialize leave balance reservations and attendance operations. SQLite does not implement row locks and is intended for local evaluation, not concurrent HR operations.

## SMTP and approval emails

Set:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<your SMTP server>
EMAIL_PORT=587
EMAIL_HOST_USER=<service account>
EMAIL_HOST_PASSWORD=<secret supplied through your host>
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=<verified sender>
SITE_URL=https://hr.your-domain.example
```

Use a provider supporting STARTTLS on port 587. Implicit SSL on port 465 is not configured by this version. Credentials remain in the environment. Configure your sender's SPF/DKIM with your provider.

Run `python manage.py send_notifications` every minute using your service scheduler. Example Linux crontab (replace paths; use a wrapper that loads protected environment variables):

```
* * * * * /srv/peopleops/send-mail.sh
```

Example wrapper:

```bash
#!/bin/sh
set -eu
cd /srv/peopleops/app
# Supply environment securely through your service environment or a protected config.
exec /srv/peopleops/venv/bin/python manage.py send_notifications
```

The command processes up to 100 unsent notifications per run and retries failures up to 10 attempts. After fixing SMTP, run `python manage.py retry_notifications`, then `send_notifications`. Operations shows unsent/failed counts. PostgreSQL row locks prevent two workers from processing the same row simultaneously. Delivery is at least once: a worker/database crash after SMTP acceptance can cause a duplicate email on retry. SMTP acceptance does not guarantee inbox delivery; monitor provider bounce events. Outbox contains recipient and message content: restrict database access and apply your retention policy.

Approval emails contain a link, with no bearer approval token and no leave reason. The approver must sign in and submit a CSRF-protected form. GET links never approve requests. Password-reset emails use Django's built-in synchronous mail path rather than the leave outbox. Test password resets separately after SMTP setup; HTTPS and correct public host are essential.

## Production deployment

1. Provision PostgreSQL and a supported Python runtime. Install requirements in an isolated virtual environment.
2. Set `DJANGO_DEBUG=0`, a random `DJANGO_SECRET_KEY`, precise `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS=https://your-domain`, SMTP settings and `SITE_URL`. Generate a key using `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Keep it private.
3. Back up existing data, run `python manage.py migrate`, then `python manage.py collectstatic --noinput`.
4. Run `python manage.py check --deploy` in the actual production environment. Resolve findings.
5. Serve with a WSGI server, e.g., `gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3`. Windows local evaluation uses runserver; use a supported production WSGI host for deployment.
6. Put a TLS-enabled reverse proxy in front. Serve `/static/` from `staticfiles/`. Redirect HTTP to HTTPS. Configure trusted proxy HTTPS detection in settings only for a proxy you control that strips/replaces spoofed forwarded headers. `SECURE_PROXY_SSL_HEADER` is deliberately not assumed; without correct HTTPS detection a TLS-terminating proxy can produce redirect loops.
7. Schedule the notification command every minute and `python manage.py clearsessions` daily. Monitor failures, HTTP errors, backups, and outbox counts.
8. Add reverse-proxy login/password-reset rate limits and monitoring; this app does not implement distributed login throttling or MFA. Restrict HR access and use strong unique passwords.
9. Run the acceptance checklist before entering live personnel data.

Django sessions, password hashing, CSRF protection, escaping, security headers and ORM queries are used. Production turns on HTTPS redirects, secure cookies and HSTS. Deploy behind HTTPS from the start. Do not use runserver for production. Reference: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

## Backups and rollback

Back up PostgreSQL with your managed provider or `pg_dump` using secure credentials; encrypt backups and test restore into an isolated database. Back up configuration separately without publishing secrets. Migrate against a restored staging copy before upgrades. For SQLite local backups, stop the app and copy `db.sqlite3`.

Keep the prior application version and migration state. On a failed release, stop web and email workers, restore the pre-release backup and prior code together, then validate counts and approvals before reopening. Do not reverse migrations blindly against live data. Retain audit events and decision records; deactivate accounts rather than deleting employees. Configure a company retention/deletion process before live use: automated privacy erasure and archival are not implemented.
