"""
GigShield Database Models
=========================
All SQLAlchemy models for NeonDB (PostgreSQL)
"""

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    platform = db.Column(db.String(50))          # zomato, swiggy, amazon, flipkart, zepto, blinkit
    partner_id = db.Column(db.String(100))        # Platform-specific delivery partner ID
    pincode = db.Column(db.String(10))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='user')  # user | admin | partner
    policy_accepted = db.Column(db.Boolean, default=False)
    policy_accepted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp_secret = db.Column(db.String(10))
    otp_expires_at = db.Column(db.DateTime)
    two_fa_enabled = db.Column(db.Boolean, default=True)

    policies = db.relationship('Policy', backref='user', lazy=True)
    claims = db.relationship('Claim', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    reports = db.relationship('Report', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_otp(self, length=6):
        import random
        self.otp_secret = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        from datetime import timedelta
        self.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        return self.otp_secret

    def verify_otp(self, otp):
        if not self.otp_secret or not self.otp_expires_at:
            return False
        if datetime.utcnow() > self.otp_expires_at:
            return False
        return self.otp_secret == otp


class Policy(db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tier = db.Column(db.String(20), nullable=False)  # basic/gold/platinum/diamond/diamond+
    weekly_premium = db.Column(db.Float, nullable=False)
    daily_payout = db.Column(db.Float, nullable=False)
    max_claimable_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')  # active | paused | expired | cancelled
    start_date = db.Column(db.Date, nullable=False)
    next_billing_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    claims = db.relationship('Claim', backref='policy', lazy=True)


class DailyRecord(db.Model):
    """Records whether a delivery was made on a given day — clears payout eligibility"""
    __tablename__ = 'daily_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    delivery_verified = db.Column(db.Boolean, default=False)  # Verified via partner API
    deliveries_made = db.Column(db.Integer, default=0)        # Count from partner API
    weather_disruption = db.Column(db.Boolean, default=False)
    social_disruption = db.Column(db.Boolean, default=False)
    disruption_type = db.Column(db.String(100))               # e.g. "heavy_rain", "curfew"
    disruption_severity = db.Column(db.String(20))            # full | half
    payout_eligible = db.Column(db.Boolean, default=False)
    payout_amount = db.Column(db.Float, default=0.0)
    payout_voided = db.Column(db.Boolean, default=False)      # True if deliveries_made > 0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Claim(db.Model):
    __tablename__ = 'claims'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    claim_date = db.Column(db.Date, nullable=False)
    disruption_type = db.Column(db.String(100))
    disruption_evidence = db.Column(db.Text)                  # JSON: weather data snapshot
    payout_amount = db.Column(db.Float)
    payout_type = db.Column(db.String(10))                    # full | half
    status = db.Column(db.String(20), default='pending')      # pending | approved | rejected | paid
    fraud_score = db.Column(db.Float, default=0.0)            # 0-1 (higher = more suspicious)
    fraud_flags = db.Column(db.Text)                          # JSON array of flag strings
    auto_approved = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payment_type = db.Column(db.String(20))                   # premium | payout
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(5), default='INR')
    razorpay_order_id = db.Column(db.String(100))             # >>> RAZORPAY ORDER ID
    razorpay_payment_id = db.Column(db.String(100))           # >>> RAZORPAY PAYMENT ID
    razorpay_signature = db.Column(db.String(200))            # >>> RAZORPAY SIGNATURE
    status = db.Column(db.String(20), default='pending')      # pending | completed | failed | refunded
    week_start = db.Column(db.Date)                           # For weekly payout batch
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    claims = db.relationship('Claim', backref='payment_ref', lazy=True,
                             foreign_keys='Claim.payment_id')


class Report(db.Model):
    """User-submitted payment dispute reports — reviewed by LLM"""
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(50))                    # payment_issue | missed_payout | app_crash | other
    description = db.Column(db.Text, nullable=False)
    evidence_urls = db.Column(db.Text)                        # JSON array of uploaded proof URLs
    report_date = db.Column(db.Date)
    incident_date = db.Column(db.Date)
    platform_affected = db.Column(db.String(50))
    llm_review = db.Column(db.Text)                           # LLM analysis output
    llm_verdict = db.Column(db.String(20))                    # valid | invalid | needs_review
    llm_confidence = db.Column(db.Float)
    admin_decision = db.Column(db.String(20))                 # approved | rejected | escalated
    admin_notes = db.Column(db.Text)
    payout_triggered = db.Column(db.Boolean, default=False)
    payout_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='submitted')    # submitted | under_review | resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)


class WeatherLog(db.Model):
    """Cached weather API responses for audit trail"""
    __tablename__ = 'weather_logs'
    id = db.Column(db.Integer, primary_key=True)
    pincode = db.Column(db.String(10))
    city = db.Column(db.String(100))
    log_date = db.Column(db.Date)
    log_time = db.Column(db.DateTime, default=datetime.utcnow)
    temperature_c = db.Column(db.Float)
    rainfall_mm = db.Column(db.Float)
    wind_kmh = db.Column(db.Float)
    aqi = db.Column(db.Integer)
    visibility_m = db.Column(db.Integer)
    weather_main = db.Column(db.String(50))
    weather_desc = db.Column(db.String(200))
    raw_response = db.Column(db.Text)                         # Full JSON from API
    disruption_triggered = db.Column(db.Boolean, default=False)
    disruption_type = db.Column(db.String(100))


class AuditLog(db.Model):
    """Full audit trail for compliance"""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    actor_role = db.Column(db.String(20))
    action = db.Column(db.String(100))
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
