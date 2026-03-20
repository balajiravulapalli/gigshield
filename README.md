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
|------------|----------------|--------------|-------------------|
| Basic      | Rs. 49         | Rs. 200      | 3                 |
| Gold       | Rs. 99         | Rs. 350      | 4                 |
| Platinum   | Rs. 149        | Rs. 500      | 5                 |
| Diamond    | Rs. 199        | Rs. 700      | 6                 |
| Diamond+   | Rs. 249        | Rs. 900      | 7                 |

---

## Qualifying Disruption Triggers

Environmental: Heavy rainfall above 15mm per hour, temperature above 42 degrees
Celsius, wind speed above 60 km/h, visibility below 200 metres, severe flooding.

Social: Government-declared curfews, city-wide strikes, sudden zone closures.

Platform: Verified app-wide outages exceeding 3 hours, confirmed via
Downdetector and partner API data.

---

 
## Local Setup

1. Clone the repository
```
git clone https://github.com/balajiravulapalli/gigshield.git
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

## Adversarial Defense & Anti-Spoofing Strategy

### The Market Crash Scenario

A coordinated fraud ring used 500 fake accounts with GPS spoofing to
drain a platform's liquidity pool. GigShield's multi-layer defense
makes this attack economically unviable.

---

### How We Spot the Faker

**GPS Trajectory Consistency**
Real workers show movement traces with logical paths and dwell times.
Spoofers teleport. Any location delta exceeding 120 km/h between
15-minute pings is flagged automatically.

**Partner API Cross-Verification**
We verify with the delivery platform that the partner's app was
online with zero completed orders. No active app session during the
claimed disruption window means automatic rejection.

**Cluster Detection**
10 or more claims from the same IP subnet or pincode within a 2-hour
window triggers a full cluster hold before any payout is released.

**Account Seasoning Rule**
Accounts under 14 days old with no verified delivery history cannot
receive automatic payouts. All claims go to manual review.

**Device Fingerprinting**
Every session captures browser agent, timezone, and network type.
Identical fingerprints across multiple accounts are flagged as
synthetic.

---

### Flagging Bad Actors Without Punishing Honest Workers

| Fraud Score | Action |
|-------------|--------|
| Below 0.3 | Auto approved, paid end of day |
| 0.3 to 0.6 | 24-hour soft hold, auto releases if checks pass |
| 0.6 to 0.8 | Manual review, decision within 48 hours |
| Above 0.8 | Auto rejected, full appeal available via in-app report |

Honest workers caught in a fraud cluster are never permanently
blocked. They move to manual review or the appeal queue with
LLM-assisted human oversight.

---

### Liquidity Pool Protection

If total payout liability for a single disruption event exceeds
3 times the average daily payout volume for that pincode cluster,
automatic payouts pause and remaining claims enter manual review.
Claims already approved before the cap are unaffected.

---

### Summary

GPS spoofing alone cannot defeat GigShield. A fraud ring must
simultaneously spoof a delivery platform session, a device
fingerprint, a realistic movement trace, and a multi-week account
history. The attack surface is too wide to exploit at scale.
Open http://localhost:5000 in your browser.

---

## Team

| Name                       | Role                  | GitHub |
|----------------------------|-----------------------|--------|
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

---
