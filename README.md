# Volunteer Hours

Flask site where students log volunteer hours and admins approve them.

## Local development

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
flask --app app import-students "path\to\student_list.xlsx"
flask --app app run
```

Without `DATABASE_URL` the app uses `sqlite:///dev.db`. Without `SECRET_KEY` it uses a
development-only key, which is refused outside testing mode.

Tests: `python -m pytest -v`

## Deploy to Render

`render.yaml` defines a Python web service and a Postgres database. Secrets are not stored in the repo.

1. Push the repository to GitHub and create a Blueprint (or web service) in Render from it.
2. In the Render dashboard, open the web service's **Environment** tab and set:
   - `SMTP_USER` and `SMTP_PASSWORD`: the Gmail sender account and its App Password
   - `ADMIN_LOGIN` and `ADMIN_PASSWORD`: the admin credentials
   - `SECRET_KEY` is generated automatically by Render (`generateValue`); leave it as is.
   - `DATABASE_URL` is wired to the Render Postgres database automatically.
3. Wait for the first deploy to finish.
4. Open the web service's **Shell** and run the migrations:
   ```
   flask db upgrade
   ```
5. **Restart the web service** (Manual Deploy > Restart, or the restart button). The admin account is created from `ADMIN_LOGIN` / `ADMIN_PASSWORD` on app start, and this only happens once the tables exist.
6. Upload the student list file to the Render shell (never commit it to the repo), then import it:
   ```
   flask --app app import-students "<path to the student list>"
   ```
   Re-running the import updates existing students.

After deploy, open `/login` on the Render URL to confirm the site is up.
