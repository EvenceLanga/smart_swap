# SkillSwap Django Project (Skeleton)

This repository contains a starter Django project and app for the **SkillSwap** platform.
It provides models, basic views, templates and URLs to help you start development quickly.

## Setup (local)

1. Create a virtualenv and activate it (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS / Linux
   venv\Scripts\activate    # Windows
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Apply migrations and create a superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Notes
- This project uses Django's built-in `User` model and a `Profile` model (OneToOne) for extra fields.
- Database: SQLite by default (for simplicity). For production, switch to PostgreSQL and set `DEBUG = False` in settings.
- The `core` app contains models for Skill, SkillRequest, Review and Message.
- Use the admin panel to inspect and manage data: http://127.0.0.1:8000/admin/

If you'd like, I can:
- Add Django REST Framework endpoints (API) for mobile apps.
- Add React frontend or React + DRF full-stack scaffolding.
- Implement more detailed unit tests and CI config.
