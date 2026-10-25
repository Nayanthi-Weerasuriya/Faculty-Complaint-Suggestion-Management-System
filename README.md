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

See [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md) for the proposal checklist, corrected defects, cleanup list, definitions and deployment tasks.

AI assistance was used to review the proposal, implement and clean code, and create regression tests. Faculty pilot testing, hosting approval and training still require human completion.


## Portal styling

The supplied FMSC theme is kept in `static/css/fmsc-theme.css` and loaded after Bootstrap. `static/css/portal.css` holds portal layout and compatibility adjustments, including fixed navigation, responsive menus, readable status accents and authentication cards. The public landing page has its own scoped layout in `static/css/landing.css`, adapting the supplied report-cover design with a maroon background, floating illustrative case cards, white heading and saffron accents. These public case previews are examples and do not expose live case records. Legacy inline navy overrides were removed so the theme applies consistently. Fonts use Bricolage Grotesque and Figtree through Google Fonts, with local system fallbacks when unavailable. Django's built-in administration keeps its own interface.


## Final review and group handoff

The final audit is in [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md). It records remaining requirements and deployment gaps without claiming full compliance. For the two-member file responsibility map and branch plan, see [docs/CONTRIBUTION_HANDOFF.md](docs/CONTRIBUTION_HANDOFF.md) and [docs/FILE_INVENTORY.csv](docs/FILE_INVENTORY.csv). Existing authorship and repository history should be preserved.
