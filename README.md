# AI Hospital Recommendation Assistant

Flask web application that recommends hospitals using symptom input, disease mapping, optional `.pkl` ML inference, location-aware ranking, booking, history, chatbot support, and admin hospital management.

## Features

- User signup and login
- Symptom or disease input
- Severity-aware hospital ranking
- Location-based recommendation scoring
- Emergency prioritization for high severity
- Appointment booking
- User recommendation history
- Chatbot endpoint
- Admin dashboard for hospital CRUD and usage stats
- English and Hindi UI labels

## Project Structure

- `app.py`: Flask app entrypoint
- `routes/`: API blueprints
- `services/`: business logic
- `models/`: request schemas
- `database/`: DB helpers and SQL schema
- `templates/`: frontend HTML
- `static/`: CSS and JavaScript
- `utils/`: helpers, translator, model loader

## MySQL Setup

1. Create a MySQL database named `hospital_recommendation`.
2. Open `database/mysql_schema.sql` in MySQL Workbench and execute it.
3. Set environment variables:

```powershell
$env:DB_ENGINE="mysql"
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_DATABASE="hospital_recommendation"
```

## ML Model Connection

1. Place your trained `.pkl` model at `ai/hospital_model.pkl`, or set:

```powershell
$env:MODEL_PATH="C:\path\to\your\model.pkl"
```

2. The loader tries common `predict()` input shapes. If your notebook model expects custom preprocessing, wrap it in a pipeline before exporting.

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Email Notifications

Appointment confirmations can be sent with SMTP or Resend. For Gmail SMTP, set:

```powershell
$env:EMAIL_PROVIDER="smtp"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="your_email@gmail.com"
$env:SMTP_PASSWORD="your_gmail_app_password"
$env:SMTP_SENDER_EMAIL="your_email@gmail.com"
```

If using Resend in test mode, Resend only sends to the verified account email. To send to other users, verify a sending domain in Resend and use that domain in `SMTP_SENDER_EMAIL`.

## Free Deployment Suggestions

- Render: Flask app + managed MySQL
- Railway: Flask service + MySQL plugin
- PythonAnywhere: simple Flask hosting
- Replit: quick demo deployment

## Notes

- SQLite works by default for local development.
- Seed data is inserted automatically on first run.
- To access admin endpoints, log in first. If needed, set a user `is_admin=1` manually in the database.
