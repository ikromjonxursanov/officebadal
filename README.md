# OfficeBadal

Simple internal office management system for tracking monthly contributions, duty rotation, expenses, and Telegram reminders.

## Features
- User management
- Monthly contribution tracking
- Payment history
- Duty rotation management
- Expense tracking
- Telegram reminders via bot and Celery

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in the values.
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the Django server:
   ```bash
   python manage.py runserver
   ```
6. Start Celery worker (optional for reminders):
   ```bash
   celery -A config worker -l info
   ```
7. Start Celery beat (optional for scheduled tasks):
   ```bash
   celery -A config beat -l info
   ```

## Admin
Open the admin panel at:
```text
http://localhost:8000/admin/
```
