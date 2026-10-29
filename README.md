# FMSC Complaint and Suggestion Management Portal

Django application for students and lecturers to submit faculty complaints and suggestions, coordinators to review and assign cases, authorities to record progress and resolution, and faculty management to monitor reports.

## Run locally

Python 3.10+ is supported by the dependency ranges; final checks were run with Python 3.14 and the installed Django version. From this project folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. A superuser can configure users, their roles, categories and authorities in `/admin/`. Set each authority officer's assigned authority before use. Students and lecturers submit cases; coordinators review/assign/reject/reassign and confirm closure; assigned authorities update progress; management has read-only reports; system administrators maintain configuration and download database backups.

For optional local demonstration data only:

```powershell
python manage.py seed_data
```

New demonstration accounts use `password123`: `student1`, `student2`, `lecturer1`, `admin_officer`, `maint_head`, `it_head`, `exam_officer`, `dean_management`, and `admin`. Existing passwords are retained. Do not use demonstration credentials for a public deployment.

## Public access and registration

The common landing page is `/`. Existing reporting-user home pages are now at `/home/`; all role-specific dashboards retain their previous URLs. The navigation and login page link to public registration at `/accounts/register/`.

Students and lecturers can register with their name, username, university email, registration/staff ID, department and password. Registration cannot create privileged accounts. New accounts remain inactive until the email verification link is opened and confirmed. Links expire after 24 hours, can only be used once, and are invalidated when a replacement is sent. Requests to resend are limited to one per minute. Existing user accounts and demo logins retain their current access.

The default accepted email domain is `sjp.ac.lk`, including its subdomains. Set `UNIVERSITY_EMAIL_DOMAINS` to a comma-separated list of approved domains if the faculty uses additional domains. This verifies mailbox ownership; it is not an integration with university student or staff records. Both public roles only receive reporting permissions.

While the console email backend is in use, verification and password-reset emails are printed in the server terminal rather than delivered to a real inbox. For local demonstrations, the registration confirmation page also shows **Open verification link** for the account just created in that browser. Click it, choose **Verify email**, then sign in. This preview requires debug mode, the console email backend and a localhost address; it is hidden with SMTP or production settings. Set `LOCAL_EMAIL_PREVIEW_ENABLED=false` to disable it explicitly. Other browsers and resend requests for existing accounts do not receive someone else's verification link. Configure SMTP as described below before inviting real users. Password-reset links remain available in the server terminal during local testing.

Verified self-registered users cannot replace their email through profile editing. They must contact the System Administrator to change it. Staff, authority, management and administrator accounts are created by the System Administrator; public registration never grants those roles.

## Workflow

Submit → review → accept/assign → progress or request information → solve with resolution note → coordinator confirms closure. The reporter can reply on an active case and reopen a solved/closed case if the resolution is unsatisfactory. Reopened cases return to coordinator review. Invalid submissions can be rejected with a reason.

Evidence is optional: JPG/JPEG/PNG/WEBP or MP4/MOV/AVI/MKV, maximum 25 MB. Both evidence forms validate actual content. Videos must have a readable video stream and duration no greater than `MAX_VIDEO_DURATION_SECONDS` (default 120). The video inspection executable is bundled by imageio-ffmpeg. The default duration is a project policy choice because the proposal does not specify a numeric limit.

Evidence is served only through authenticated attachment URLs. Keep the media directory private in hosting configuration.

## Email and configuration

The local email backend prints messages to the development console. To deliver email, set these environment variables before starting the application:

- `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST`, `EMAIL_PORT` (default 587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS=true` and `DEFAULT_FROM_EMAIL`

Notifications and password reset use the configured backend. In-app notifications remain available if an email delivery attempt fails; failures are logged for investigation.

For deployment, set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false` and `DJANGO_ALLOWED_HOSTS` (comma-separated). Run `python manage.py check --deploy` and configure HTTPS and secure cookies at the hosting environment. Local accounts are used; external university SSO is not configured.

## Reminders and backups

```powershell
python manage.py send_pending_reminders --days 7
python manage.py backup_portal
```

Schedule both commands daily with your hosting platform or Windows Task Scheduler using the virtual environment's Python and the project folder as the working directory. Reminders target the responsible unit, or the coordinator when unassigned, and avoid duplicates within the same day. Backups are ZIP archives under `backups/`, containing the SQLite database and evidence files. Use `--directory` for a different backup destination. Scheduling and retention are hosting responsibilities and are not automatically installed.

The system dashboard's download includes the database only. For restoration, stop the app, preserve the current data, restore the archive's `db.sqlite3` and `media/` into the project folder, and restart with the matching application version. Test restoration before relying on scheduled backups.

## Validation and requirements

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

OpenAI Codex assisted with proposal review, implementation, UI changes, debugging, code cleanup, regression tests and documentation. Changes were checked using automated tests, Django system checks and migration checks. Team members should explain their own review, testing and modifications during the presentation. Faculty pilot testing, hosting approval and training still require human completion.

Remaining external steps: enter approved SMTP and hosting values, verify delivery to a real inbox, activate maintenance scheduling on the target host, and conduct faculty acceptance and load testing. An isolated database/evidence restore regression test is included; a host-level restore rehearsal is still needed. The application is not yet verified for production use.


## Portal styling

The supplied FMSC theme is kept in `static/css/fmsc-theme.css` and loaded after Bootstrap. `static/css/portal.css` holds portal layout and compatibility adjustments, including fixed navigation, responsive menus, readable status accents and authentication cards. The public landing page has its own scoped layout in `static/css/landing.css`, matching the supplied homepage reference with a maroon hero, floating illustrative case cards, off-white content, numbered process cards, a cream FAQ panel and saffron accents. These public case previews are examples and do not expose live case records. Legacy inline navy overrides were removed so the theme applies consistently. Fonts use Bricolage Grotesque and Figtree through Google Fonts, with local system fallbacks when unavailable. Django's built-in administration keeps its own interface.


## Reporting and workflow safeguards (29 October 2026)

Management chart proportions use the filtered case counts, including empty results. The coordinator filter exposes inclusive submission date bounds and shows validation errors for invalid or reversed ranges. Authority pending totals and average ages both use Assigned, Not Started, In Progress and Waiting for Information; units with no pending cases are omitted, while historical cases remain in detailed reports.

Before assigning a case, create or activate a user with the Relevant Authority role and assign that user to the receiving unit. An active unit without an active Authority user cannot receive assignments. Cases, attachments, comments and audit records are read-only in Django administration, including for superusers; use the role-specific portal to perform workflow changes and preserve notifications, timestamps and audit history. User, category and authority configuration remains available in administration.

Audit IP addresses use the direct connection address. Forwarded headers are ignored unless a trusted proxy policy is implemented.

## Production and email setup

`.env.example` is a configuration template; Django does not load it automatically. Copy it to `.env`, replace every placeholder, then load it into the current PowerShell process:

```powershell
Copy-Item .env.example .env
# Edit .env locally. Never commit or share its credentials.
. .\scripts\load-environment.ps1
python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py test_email --to your-own-address@example.edu
```

The test command sends one explicit SMTP test message. SMTP acceptance does not prove inbox receipt: confirm the message in the inbox/spam folder. Do not run it until the university-approved sender, server and credentials are configured. Port 587 normally uses TLS; if the provider requires implicit SSL (commonly port 465), use EMAIL_USE_TLS=false and EMAIL_USE_SSL=true.

With DJANGO_DEBUG=false, HTTPS redirect, secure session/CSRF cookies and one-year HSTS are enabled. A strong secret and explicit hosts are required. Serve static files from STATIC_ROOT using the hosting platform/web server after collectstatic, run the Django WSGI/ASGI app with the host's production server, and keep media private. Set the trusted-proxy option only if the proxy removes client-supplied forwarded headers and sets the HTTPS header itself. HSTS subdomain coverage and preload are deliberately disabled until the university approves their domain-wide implications (then set DJANGO_HSTS_INCLUDE_SUBDOMAINS and DJANGO_HSTS_PRELOAD to true); Django deployment checks flag those two opt-ins. Local development remains available without .env using debug mode and console email.

## Prepared maintenance scripts

No scheduled task is installed automatically. To test backup/reminder execution manually on the intended host:

```powershell
.\scripts\run-maintenance.ps1
```

The runner loads .env if present, uses venv\Scripts\python.exe, backs up database/evidence first, then sends reminders for cases unchanged for seven days. It stops on command errors. Customize with `-PythonPath` or `-ReminderDays`. Keep backups private and configure off-machine storage and a retention policy with the university; the script does not delete older backups.

When ready, install the prepared daily Windows task (09:00 in that computer's local timezone):

```powershell
.\scripts\install-maintenance-task.ps1 -At '09:00'
```

This runs with your current user's permissions while signed in, starts missed runs when available and prevents overlapping runs. It does not replace an existing task. For an always-on university server, configure the same management commands through its scheduler and service account instead. The machine must be on and have access to its configuration, Python and backup destination. Review task history and email delivery logs after activation.

## Final acceptance rehearsal

Use disposable demo data and accounts, with both members present. Demonstrate registration/verification and login; complaint and suggestion submission with image/video validation; review, rejection, assignment and reassignment; progress and clarification replies; mandatory resolution notes and solved notification; closure/reopening; authority maintenance; every status summary and report filter; cross-user attachment denial; reminder deduplication; and backup recovery in a separate location. Compare reported counts to the prepared records and verify delivered email independently. Record actual results and faculty feedback; automated tests are not faculty acceptance sign-off.

The compact status summaries cover total, attempted, not attempted, open, not started, urgent, normal, solved, closed and rejected. Coordinator summaries follow submission dates; management summaries follow all report filters. Open follows the proposal definition (not closed), while active workflow controls exclude solved/closed/rejected.
