# NDMS — National Disaster Management System

Django web application for citizens to report disasters and receive alerts, and for administrators to verify reports and manage disasters, agencies, notifications and support requests.

## Features
- Citizen portal: registration, login, Google sign-in, incident reports with photos, report history, alerts, notifications, profile/avatar, settings, support requests, feedback.
- Admin portal (`/admin/`): dashboard, users, reports, disasters, disaster types, emergency agencies, response updates, notifications, support, feedback.
- Password reset by email, Terms & Privacy acceptance.

## Stack
Django 6.0.3 (needs Python 3.12+), SQLite, WhiteNoise, Pillow, python-dotenv.

## Local setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env (see below)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
For local HTTP development set `DJANGO_DEBUG=True` in `.env`.

## Environment variables
See `.env.example`. `DJANGO_SECRET_KEY` is required; with `DJANGO_DEBUG=False` the app refuses to start unless it is 50+ random characters. Never commit `.env`.

## Google OAuth
Create an OAuth 2.0 Web client in Google Cloud Console and add the redirect URI `https://<your-domain>/login/google/callback/`. Set `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`. Google sign-in never opens administrator accounts.

## Email
Set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`. Without `EMAIL_HOST` emails print to the console and password reset does NOT reach real users.

## PythonAnywhere deployment
1. Upload/clone the project, e.g. `~/ndms`.
2. `mkvirtualenv ndms --python=python3.12` (or newer), then `pip install -r requirements.txt`.
3. Set the environment variables in the WSGI file (before the `get_wsgi_application()` call) using `os.environ[...]`, or put a `.env` in the project root.
4. `python manage.py migrate` and `python manage.py collectstatic --noinput`.
5. Web tab -> Static files:
   - URL `/static/` -> `<project>/staticfiles`
   - URL `/media/` -> `<project>/media`
6. Web tab: set virtualenv path, force HTTPS, then Reload.
Uploaded files are served by PythonAnywhere's `/media/` mapping (Django does not serve media when `DEBUG=False`).

## Security notes
- Rotate any credential that was ever committed or shared (see the audit report).
- `.env`, `db.sqlite3`, `media/`, `staticfiles/` are git-ignored.
- Run `python manage.py check --deploy` with production variables before release.

## Tests
```bash
python manage.py test
```
