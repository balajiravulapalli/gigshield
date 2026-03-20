"""
GigShield Configuration
=======================
╔══════════════════════════════════════════════════════════════════╗
║  DEVELOPER GUIDE: ALL API KEYS ARE MARKED WITH # >>> KEY HERE   ║
║  Search for "# >>>" to find every integration point             ║
╚══════════════════════════════════════════════════════════════════╝

Replace placeholder strings with your actual keys before deployment.
"""

import os

class Config:
    # ─────────────────────────────────────────────
    # FLASK CORE
    # ─────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING'

    # ─────────────────────────────────────────────
    # >>> NEONDB / POSTGRESQL CONNECTION
    # ─────────────────────────────────────────────
    # Get from: https://neon.tech → Project Settings → Connection String
    # Format: postgresql://user:password@host/dbname?sslmode=require
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://neondb_owner:npg_3aNspWgC8lEZ@ep-bitter-pine-amm1eoyu-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'  # >>> INSERT NEONDB URL HERE
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ─────────────────────────────────────────────
    # >>> FLASK-MAIL (OTP & Notifications)
    # ─────────────────────────────────────────────
    # Recommended: Use Gmail App Password or SendGrid SMTP
    # ─────────────────────────────────────────────
    # >>> FLASK-MAIL (OTP & Notifications) — ZOHO MAIL
    # ─────────────────────────────────────────────
    MAIL_SERVER = 'smtp.zoho.in'          # Use smtp.zoho.com if your account is global (non-India)
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'balaji@bittyboomers.tech'  # >>> Your Zoho email
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'T19aKzfmq7it'      # >>> Your Zoho password or App-Specific Password
    MAIL_DEFAULT_SENDER = ('GigShield', MAIL_USERNAME)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'balaji@bittyboomers.tech'        # >>> Your admin inbox
    # ─────────────────────────────────────────────
    # >>> OPENWEATHERMAP API (Weather Triggers)
    # ─────────────────────────────────────────────
    # Free tier: https://openweathermap.org/api → Current Weather Data
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY') or 'YOUR_OPENWEATHER_KEY'  # >>> INSERT KEY HERE
    OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'

    # ─────────────────────────────────────────────
    # >>> RAZORPAY (Payment Gateway - Test Mode)
    # ─────────────────────────────────────────────
    # Test keys from: https://dashboard.razorpay.com → Settings → API Keys
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID') or 'rzp_test_YOUR_KEY_ID'          # >>> INSERT KEY ID HERE
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET') or 'YOUR_RAZORPAY_SECRET'   # >>> INSERT SECRET HERE

    # ─────────────────────────────────────────────
    # >>> CLOUDFLARE (CDN / DNS / Turnstile CAPTCHA)
    # ─────────────────────────────────────────────
    # Turnstile keys: https://dash.cloudflare.com → Turnstile
    CLOUDFLARE_TURNSTILE_SITE_KEY = os.environ.get('CF_SITE_KEY') or 'YOUR_TURNSTILE_SITE_KEY'    # >>> INSERT SITE KEY
    CLOUDFLARE_TURNSTILE_SECRET_KEY = os.environ.get('CF_SECRET_KEY') or 'YOUR_TURNSTILE_SECRET'  # >>> INSERT SECRET KEY

    # ─────────────────────────────────────────────
    # >>> AI FRAUD DETECTION MODEL (HuggingFace)
    # ─────────────────────────────────────────────
    # See utils/fraud_detection.py for model insertion point
    # Recommended: Plug in your HuggingFace Inference API key
    HUGGINGFACE_API_KEY = os.environ.get('HF_API_KEY') or 'YOUR_HUGGINGFACE_API_KEY'  # >>> INSERT HF KEY HERE
    # Model endpoint — insert your trained model name here
    FRAUD_MODEL_ENDPOINT = os.environ.get('FRAUD_MODEL') or 'YOUR_HUGGINGFACE_MODEL_ID'  # >>> INSERT MODEL ID HERE

    # ─────────────────────────────────────────────
    # >>> ANTHROPIC API (LLM for Claims Review)
    # ─────────────────────────────────────────────
    # https://console.anthropic.com → API Keys
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY') or 'YOUR_ANTHROPIC_API_KEY'  # >>> INSERT KEY HERE

    # ─────────────────────────────────────────────
    # ZOMATO/SWIGGY/PARTNER API STUBS
    # ─────────────────────────────────────────────
    # These are mock stubs. Replace with real partner API credentials when available.
    ZOMATO_API_KEY = os.environ.get('ZOMATO_API_KEY') or 'ZOMATO_PARTNER_API_KEY'        # >>> INSERT WHEN AVAILABLE
    AMAZON_API_KEY = os.environ.get('AMAZON_API_KEY') or 'AMAZON_FLEX_API_KEY'           # >>> INSERT WHEN AVAILABLE
    SWIGGY_API_KEY = os.environ.get('SWIGGY_API_KEY') or 'SWIGGY_PARTNER_API_KEY'        # >>> INSERT WHEN AVAILABLE

    # ─────────────────────────────────────────────
    # DOWNDETECTOR INTEGRATION
    # ─────────────────────────────────────────────
    # Downdetector doesn't have an official API — we use scraping/RSS
    DOWNDETECTOR_BASE_URL = 'https://downdetector.in'  # No key needed; see utils/downdetector.py

    # ─────────────────────────────────────────────
    # OTP CONFIG
    # ─────────────────────────────────────────────
    OTP_EXPIRY_MINUTES = 10
    OTP_LENGTH = 6

    # ─────────────────────────────────────────────
    # INSURANCE TIERS CONFIG
    # ─────────────────────────────────────────────
    INSURANCE_TIERS = {
        'basic':     {'weekly_premium': 49,  'daily_payout': 200, 'max_days': 3, 'color': '#B89685'},
        'gold':      {'weekly_premium': 99,  'daily_payout': 350, 'max_days': 4, 'color': '#FBBC00'},
        'platinum':  {'weekly_premium': 149, 'daily_payout': 500, 'max_days': 5, 'color': '#BFADA3'},
        'diamond':   {'weekly_premium': 199, 'daily_payout': 700, 'max_days': 6, 'color': '#504746'},
        'diamond+':  {'weekly_premium': 249, 'daily_payout': 900, 'max_days': 7, 'color': '#B6244F'},
    }

    # Weather thresholds for automatic claim triggers
    WEATHER_THRESHOLDS = {
        'heavy_rain_mm': 15.0,      # mm/hour
        'extreme_heat_c': 42.0,     # Celsius
        'extreme_cold_c': 5.0,      # Celsius
        'high_wind_kmh': 60.0,      # km/h
        'aqi_severe': 301,           # Air Quality Index
        'visibility_m': 200,         # metres
    }
