# 🛡️ GigShield — AI-Powered Parametric Insurance Platform

India's first AI-enabled income protection platform for delivery partners.
Built for the Guidewire DEVTrails 2026 hackathon.

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd gigshield
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Open **`config.py`** and search for `# >>>` to find every integration point.

| Key | Where to Get | Config Variable |
|-----|-------------|----------------|
| NeonDB URL | https://neon.tech → Project → Connection String | `SQLALCHEMY_DATABASE_URI` |
| Admin Email | Your Gmail | `MAIL_USERNAME` |
| Gmail App Password | Google Account → Security → App Passwords | `MAIL_PASSWORD` |
| OpenWeatherMap | https://openweathermap.org/api | `OPENWEATHER_API_KEY` |
| Razorpay Test Key | https://dashboard.razorpay.com → Settings → API | `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` |
| HuggingFace API | https://huggingface.co/settings/tokens | `HUGGINGFACE_API_KEY` |
| Fraud Model | Your trained model on HuggingFace Hub | `FRAUD_MODEL_ENDPOINT` |
| Anthropic (LLM review) | https://console.anthropic.com | `ANTHROPIC_API_KEY` |
| Cloudflare Turnstile | https://dash.cloudflare.com → Turnstile | `CLOUDFLARE_TURNSTILE_SITE_KEY` |

### 3. Set Environment Variables (Recommended for Production)
```bash
export DATABASE_URL="postgresql://user:pass@host/gigshield?sslmode=require"
export MAIL_USERNAME="youradmin@gmail.com"
export MAIL_PASSWORD="your-app-password"
export OPENWEATHER_API_KEY="your-key"
export RAZORPAY_KEY_ID="rzp_test_xxx"
export RAZORPAY_KEY_SECRET="your-secret"
export ANTHROPIC_API_KEY="your-key"
export HF_API_KEY="your-key"
export FRAUD_MODEL="your-username/your-fraud-model"
```

### 4. Create Admin User
```python
from app import create_app, db
from models import User
app = create_app()
with app.app_context():
    admin = User(
        full_name='Admin',
        email='admin@yourdomain.com',
        phone='9999999999',
        role='admin',
        is_verified=True,
        policy_accepted=True
    )
    admin.set_password('YourSecurePassword123!')
    db.session.add(admin)
    db.session.commit()
    print('Admin created!')
```

### 5. Create Partner Users (Zomato, Amazon, etc.)
```python
partner = User(
    full_name='Zomato India',
    email='partner@zomato.com',
    phone='8888888888',
    platform='zomato',
    role='partner',
    is_verified=True,
    policy_accepted=True
)
partner.set_password('ZomatoPartner2026!')
```

### 6. Run the App
```bash
python app.py
# or for production:
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

---

## 🤖 HuggingFace Fraud Model Integration

Open `utils/fraud.py` and find `# ===== HF MODEL INSERTION POINT =====`

To plug in your trained model:
```python
# In calculate_fraud_score(), replace the fallback call with:
features = _build_feature_vector(user, claim_date, disruption_type, payout_amount, pincode)
hf_score = _call_hf_model(features)
if hf_score is not None:
    return {'score': hf_score, 'flags': [], 'verdict': _verdict(hf_score)}
```

Your model should:
- Accept JSON feature input
- Return a fraud probability between 0.0 and 1.0

---

## ⏰ Daily Payout Scheduler

The automated payout engine runs at 23:30 IST daily.
Uncomment in `app.py`:
```python
from routes.api import setup_scheduler
setup_scheduler(app)
```
Install: `pip install APScheduler pytz`

---

## 🏗️ Architecture

```
gigshield/
├── app.py              # Flask factory
├── config.py           # All API keys (>>> markers)
├── models.py           # NeonDB/PostgreSQL models
├── routes/
│   ├── auth.py         # Login, Register, OTP, 2FA
│   ├── user.py         # User dashboard
│   ├── admin.py        # Admin portal
│   ├── partner.py      # Zomato/Amazon/etc portal
│   └── api.py          # Internal API + scheduler
├── utils/
│   ├── weather.py      # OpenWeatherMap integration
│   ├── fraud.py        # AI fraud detection (HF model slot)
│   ├── payment.py      # Razorpay integration
│   ├── llm_review.py   # Anthropic LLM report reviewer
│   └── filters.py      # Jinja2 filters
└── templates/
    ├── base.html       # Layout + design system
    ├── landing.html    # Public homepage
    ├── register.html   # Registration + policy
    ├── login.html
    ├── verify_otp.html # 2FA OTP entry
    ├── user/           # Gig worker views
    ├── admin/          # Admin portal views
    └── partner/        # Partner portal views
```

---

## 🛡️ Insurance Tiers

| Tier | Weekly Premium | Daily Payout | Max Days/Week |
|------|---------------|--------------|---------------|
| Basic | ₹49 | ₹200 | 3 |
| Gold | ₹99 | ₹350 | 4 |
| Platinum | ₹149 | ₹500 | 5 |
| Diamond | ₹199 | ₹700 | 6 |
| Diamond+ | ₹249 | ₹900 | 7 |

---

## ⚠️ Coverage Scope

✅ Covered: Weather disruptions · Social/curfew disruptions · App outages
❌ Not Covered: Health · Accidents · Vehicle repairs

---

## 🎨 Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Charcoal | `#504746` | Primary backgrounds |
| Warm Brown | `#B89685` | Accents |
| Pale Blush | `#BFADA3` | Secondary text |
| Gold | `#FBBC00` | CTA / highlights |
| Crimson | `#B6244F` | Alerts / admin |
