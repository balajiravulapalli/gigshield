"""
GigShield API Routes + Daily Scheduler
========================================
- Internal API endpoints
- APScheduler for daily automated payout processing
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from models import User, Policy, Claim, Payment, DailyRecord, WeatherLog
from utils.weather import check_weather_disruption
from utils.fraud import calculate_fraud_score
from datetime import datetime, date, timedelta

api_bp = Blueprint('api', __name__)


# ─────────────────────────────────────────────
# DAILY AUTOMATED PAYOUT ENGINE
# Called by scheduler at end of day (23:30 IST)
# ─────────────────────────────────────────────

def run_daily_payout_engine():
    """
    Core automated payout logic:
    1. Get all active policies
    2. For each user, check weather disruption for their pincode
    3. Cross-check partner API for deliveries made
    4. Create claim + payment if eligible
    5. Void payout if deliveries confirmed

    >>> This function is scheduled to run daily at 23:30 IST
    >>> Register it with APScheduler in your main app startup
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        today = date.today()
        active_policies = Policy.query.filter_by(status='active').all()
        tiers = current_app.config['INSURANCE_TIERS']

        processed = 0
        payouts_issued = 0

        for policy in active_policies:
            user = User.query.get(policy.user_id)
            if not user or not user.pincode:
                continue

            # Skip if already processed today
            existing = DailyRecord.query.filter_by(
                user_id=user.id, record_date=today).first()
            if existing:
                continue

            # Check weather
            try:
                weather = check_weather_disruption(user.pincode, user.city)
            except Exception as e:
                print(f"Weather check failed for user {user.id}: {e}")
                continue

            disruption = weather.get('disruption_triggered', False)
            disruption_type = weather.get('disruption_type')
            severity = weather.get('severity')

            # Check if deliveries made (from partner daily sync)
            daily_rec = DailyRecord.query.filter_by(
                user_id=user.id, record_date=today).first()

            deliveries_made = daily_rec.deliveries_made if daily_rec else 0

            # Create daily record
            rec = DailyRecord(
                user_id=user.id,
                policy_id=policy.id,
                record_date=today,
                delivery_verified=daily_rec.delivery_verified if daily_rec else False,
                deliveries_made=deliveries_made,
                weather_disruption=disruption,
                disruption_type=disruption_type,
                disruption_severity=severity,
                payout_eligible=False
            )

            if disruption and deliveries_made == 0:
                # Eligible for payout
                payout_amount = policy.daily_payout if severity == 'full' else policy.daily_payout / 2

                # Run fraud check
                fraud_result = calculate_fraud_score(
                    user=user, claim_date=today,
                    disruption_type=disruption_type,
                    payout_amount=payout_amount,
                    pincode=user.pincode
                )

                import json
                claim = Claim(
                    user_id=user.id,
                    policy_id=policy.id,
                    claim_date=today,
                    disruption_type=disruption_type,
                    disruption_evidence=json.dumps(weather.get('weather_data', {})),
                    payout_amount=payout_amount,
                    payout_type=severity,
                    fraud_score=fraud_result['score'],
                    fraud_flags=json.dumps(fraud_result['flags']),
                    status='pending' if fraud_result['score'] >= 0.6 else 'approved',
                    auto_approved=fraud_result['score'] < 0.6
                )
                db.session.add(claim)
                db.session.flush()

                if claim.status == 'approved':
                    payment = Payment(
                        user_id=user.id,
                        payment_type='payout',
                        amount=payout_amount,
                        status='completed',
                        description=f'Auto payout — {disruption_type} ({severity} day)',
                        week_start=today - timedelta(days=today.weekday()),
                        completed_at=datetime.utcnow()
                    )
                    db.session.add(payment)
                    db.session.flush()
                    claim.payment_id = payment.id
                    payouts_issued += 1

                rec.payout_eligible = True
                rec.payout_amount = payout_amount

            elif deliveries_made > 0:
                rec.payout_voided = True

            db.session.add(rec)
            processed += 1

        db.session.commit()
        print(f"Daily engine: processed {processed} policies, issued {payouts_issued} payouts")


def setup_scheduler(app):
    """
    Set up APScheduler for daily payout engine.
    Call this from your main app factory.

    >>> Install: pip install APScheduler
    >>> Add to app.py create_app():
    >>>   from routes.api import setup_scheduler
    >>>   setup_scheduler(app)
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        scheduler = BackgroundScheduler()
        ist = pytz.timezone('Asia/Kolkata')

        # Run daily at 23:30 IST
        scheduler.add_job(
            func=run_daily_payout_engine,
            trigger=CronTrigger(hour=23, minute=30, timezone=ist),
            id='daily_payout_engine',
            name='GigShield Daily Payout Engine',
            replace_existing=True
        )

        # Weekly premium renewal check at 00:01 Monday IST
        scheduler.add_job(
            func=run_weekly_renewal,
            trigger=CronTrigger(day_of_week='mon', hour=0, minute=1, timezone=ist),
            id='weekly_renewal',
            name='Weekly Premium Renewal',
            replace_existing=True
        )

        scheduler.start()
        print("✅ GigShield scheduler started")
        return scheduler
    except ImportError:
        print("⚠️  APScheduler not installed. Run: pip install APScheduler pytz")


def run_weekly_renewal():
    """Deactivate policies with lapsed premiums"""
    from app import create_app
    app = create_app()
    with app.app_context():
        today = date.today()
        lapsed = Policy.query.filter(
            Policy.status == 'active',
            Policy.next_billing_date < today
        ).all()
        for policy in lapsed:
            policy.status = 'paused'
        db.session.commit()
        print(f"Weekly renewal: paused {len(lapsed)} lapsed policies")


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@api_bp.route('/weather/check')
@login_required
def api_weather_check():
    """Check current weather disruption status for user's pincode"""
    pincode = request.args.get('pincode', current_user.pincode)
    city = request.args.get('city', current_user.city)
    try:
        result = check_weather_disruption(pincode, city)
        return jsonify({
            'success': True,
            'pincode': pincode,
            'disruption_triggered': result['disruption_triggered'],
            'disruption_type': result['disruption_type'],
            'severity': result['severity'],
            'temperature': result['weather_data'].get('main', {}).get('temp'),
            'rain_mm': result['weather_data'].get('rain', {}).get('1h', 0),
            'wind_kmh': round(result['weather_data'].get('wind', {}).get('speed', 0) * 3.6, 1),
            'description': result['weather_data']['weather'][0]['description'] if result['weather_data'].get('weather') else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/admin/trigger-daily-engine', methods=['POST'])
@login_required
def admin_trigger_engine():
    """Manually trigger the daily payout engine (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    try:
        run_daily_payout_engine()
        return jsonify({'success': True, 'message': 'Daily engine completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/pincode/<pincode>')
def pincode_lookup(pincode):
    """Proxy for India Post pincode API"""
    import requests
    try:
        r = requests.get(f'https://api.postalpincode.in/pincode/{pincode}', timeout=5)
        return jsonify(r.json())
    except Exception:
        return jsonify([{'Status': 'Error'}])
