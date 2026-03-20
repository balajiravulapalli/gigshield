# GigShield

AI-Powered Parametric Insurance Platform for India's Gig Economy

Built for Guidewire DEVTrails 2026 University Hackathon.

---

## Problem Statement

India's platform-based delivery partners working with Zomato, Swiggy, Amazon,
Flipkart, Zepto, and Blinkit face income loss of 20 to 30 percent monthly due
to extreme weather, floods, pollution, and social disruptions like curfews and
strikes. They have no financial safety net for these uncontrollable events.

GigShield solves this by providing automated parametric income protection
insurance that triggers payouts based on real weather data, with no claim
forms required.

---

## What We Built

GigShield is a full-stack web application that provides:

- Automated income loss coverage triggered by weather and social disruptions
- Weekly premium model aligned to the gig worker pay cycle
- Zero-touch claim processing with AI fraud detection
- Dual dashboards for workers and administrators
- Partner portal for Zomato, Swiggy, Amazon, and other platforms
- Two-factor authentication via OTP email verification
- Razorpay payment integration for premium collection and payouts
- LLM-powered report review for disputed claims

Coverage is for income loss only. Health, vehicle, accident, and medical
claims are strictly excluded.

---

## Tech Stack

- Backend: Python, Flask, SQLAlchemy
- Database: NeonDB (PostgreSQL)
- Frontend: HTML, CSS, JavaScript, Jinja2 templates
- Payments: Razorpay
- Email: Zoho Mail via Flask-Mail
- Weather: OpenWeatherMap API
- AI Fraud Detection: HuggingFace Inference API
- LLM Claims Review: Anthropic Claude API
- Deployment: Render / Railway (TBD)

---

## Insurance Tiers

| Tier       | Weekly Premium | Daily Payout | Max Days Per Week |
|------------|---------------|--------------|-------------------|
| Basic      | Rs. 49        | Rs. 200      | 3                 |
| Gold       | Rs. 99        | Rs. 350      | 4                 |
| Platinum   | Rs. 149       | Rs. 500      | 5                 |
| Diamond    | Rs. 199       | Rs. 700      | 6                 |
| Diamond+   | Rs. 249       | Rs. 900      | 7                 |

---

## Qualifying Disruption Triggers

Environmental: Heavy rainfall above 15mm per hour, temperature above 42 degrees
Celsius, wind speed above 60 km/h, visibility below 200 metres, severe flooding.

Social: Government-declared curfews, city-wide strikes, sudden zone closures.

Platform: Verified app-wide outages exceeding 3 hours, confirmed via
Downdetector and partner API data.

---

## Project Structure
```
gigshield/
├── app.py                  # Flask application factory
├── config.py               # All configuration and API key placeholders
├── models.py               # SQLAlchemy database models
├── requirements.txt        # Python dependencies
├── routes/
│   ├── auth.py             # Registration, login, OTP, 2FA
│   ├── user.py             # User dashboard, policies, claims
│   ├── admin.py            # Admin portal
│   ├── partner.py          # Partner portal for platforms
│   └── api.py              # Internal API endpoints
├── utils/
│   ├── weather.py          # OpenWeatherMap integration
│   ├── fraud.py            # Fraud detection with HuggingFace model slot
│   ├── payment.py          # Razorpay integration
│   └── llm_review.py       # Anthropic LLM claims review
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── register.html
    ├── verify_otp.html
    ├── user/
    └── admin/
```

---

## Local Setup

1. Clone the repository
```
git clone https://github.com/YOUR_USERNAME/gigshield.git
cd gigshield
```

2. Create and activate a virtual environment
```
python -m venv venv
source venv/bin/activate        # Mac or Linux
venv\Scripts\activate           # Windows
```

3. Install dependencies
```
pip install -r requirements.txt
```

4. Create a .env file in the root directory and add your keys
```
DATABASE_URL=postgresql://user:password@host/gigshield?sslmode=require
MAIL_USERNAME=noreply@yourdomain.com
MAIL_PASSWORD=your_zoho_app_password
ADMIN_EMAIL=admin@yourdomain.com
OPENWEATHER_API_KEY=your_key_here
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret_here
```

5. Initialize the database and create admin user
```
python
```
```python
from app import create_app, db
from models import User

app = create_app()
with app.app_context():
    db.create_all()
    admin = User(full_name='Admin', email='admin@yourdomain.com',
                 phone='9999999999', role='admin', is_verified=True, platform='admin')
    admin.set_password('StrongPassword123')
    db.session.add(admin)
    db.session.commit()
```

6. Run the application
```
python app.py
```

Open http://localhost:5000 in your browser.

---

## Team

| Name                       | Role                 | GitHub  |
|----------------------------|----------------------|--------|
| Ravulapalli Balaji         | Backend and Database  |        |
| Munugoti Harshitha Bhavana | Frontend and UI       |        |
| Konapala Rahul Dhruva      | AI and Integrations   |        |
| Pittu Amarnath             | Payments and DevOps   |        |

---

## Important Notes

This platform covers income loss only. It does not provide health insurance,
vehicle repair coverage, accident insurance, or any medical coverage.

The .env file is gitignored. Never commit API keys or passwords to the repository.

Razorpay test keys are safe to use during development. Switch to live keys
only before production deployment.


```

---

## Step 3 — Add the .gitignore File

The Python .gitignore GitHub generates is good but add these lines to the bottom of it:
```
.env
*.env
config_local.py
instance/
__pycache__/
*.pyc
venv/
.venv/
*.sqlite3
*.db
.DS_Store
