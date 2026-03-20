"""
GigShield User Dashboard Routes
================================
All gig worker-facing views: dashboard, policy, claims, payments, reports
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from models import Policy, Claim, Payment, DailyRecord, Report, WeatherLog, AuditLog
from utils.weather import check_weather_disruption
from utils.fraud import calculate_fraud_score
from utils.payment import create_razorpay_order, verify_razorpay_payment
from datetime import datetime, date, timedelta
import json

user_bp = Blueprint('user', __name__)


@user_bp.route('/')
@login_required
def dashboard():
    active_policy = Policy.query.filter_by(user_id=current_user.id, status='active').first()
    recent_claims = Claim.query.filter_by(user_id=current_user.id).order_by(Claim.created_at.desc()).limit(5).all()
    recent_payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).limit(5).all()

    # Weekly stats
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_claims = Claim.query.filter(
        Claim.user_id == current_user.id,
        Claim.claim_date >= week_start
    ).all()
    week_payout = sum(c.payout_amount or 0 for c in week_claims if c.status == 'paid')

    # Check today's weather for user's pincode
    today_weather = None
    disruption_active = False
    if active_policy and current_user.pincode:
        try:
            today_weather = check_weather_disruption(current_user.pincode, current_user.city)
            disruption_active = today_weather.get('disruption_triggered', False)
        except Exception:
            pass

    return render_template('user/dashboard.html',
        active_policy=active_policy,
        recent_claims=recent_claims,
        recent_payments=recent_payments,
        week_payout=week_payout,
        week_claims=len(week_claims),
        today_weather=today_weather,
        disruption_active=disruption_active,
        tiers=current_app.config['INSURANCE_TIERS']
    )


@user_bp.route('/policies')
@login_required
def policies():
    all_policies = Policy.query.filter_by(user_id=current_user.id).order_by(Policy.created_at.desc()).all()
    tiers = current_app.config['INSURANCE_TIERS']
    return render_template('user/policies.html', policies=all_policies, tiers=tiers)


@user_bp.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    tiers = current_app.config['INSURANCE_TIERS']
    if request.method == 'POST':
        tier = request.form.get('tier')
        if tier not in tiers:
            return jsonify({'success': False, 'message': 'Invalid tier'}), 400

        # Check for existing active policy
        existing = Policy.query.filter_by(user_id=current_user.id, status='active').first()
        if existing:
            return jsonify({'success': False, 'message': 'You already have an active policy. Cancel it first.'})

        tier_data = tiers[tier]
        # Create Razorpay order for weekly premium
        try:
            order = create_razorpay_order(
                amount=tier_data['weekly_premium'],
                receipt=f"policy_{current_user.id}_{tier}",
                notes={'user_id': current_user.id, 'tier': tier, 'type': 'premium'}
            )
        except Exception as e:
            return jsonify({'success': False, 'message': f'Payment gateway error: {str(e)}'})

        session_data = {
            'pending_tier': tier,
            'pending_order_id': order['id']
        }
        from flask import session
        session.update(session_data)

        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': int(tier_data['weekly_premium'] * 100),
            'razorpay_key': current_app.config['RAZORPAY_KEY_ID'],
            'tier': tier,
            'tier_data': tier_data
        })

    return render_template('user/subscribe.html', tiers=tiers)


@user_bp.route('/payment-success', methods=['POST'])
@login_required
def payment_success():
    from flask import session
    data = request.json
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    # Verify payment signature
    if not verify_razorpay_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400

    tier = session.get('pending_tier')
    tiers = current_app.config['INSURANCE_TIERS']
    tier_data = tiers.get(tier)
    if not tier_data:
        return jsonify({'success': False, 'message': 'Invalid session'}), 400

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        payment_type='premium',
        amount=tier_data['weekly_premium'],
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        status='completed',
        week_start=date.today(),
        description=f'{tier.title()} Plan Weekly Premium',
        completed_at=datetime.utcnow()
    )
    db.session.add(payment)

    # Create policy
    policy = Policy(
        user_id=current_user.id,
        tier=tier,
        weekly_premium=tier_data['weekly_premium'],
        daily_payout=tier_data['daily_payout'],
        max_claimable_days=tier_data['max_days'],
        status='active',
        start_date=date.today(),
        next_billing_date=date.today() + timedelta(weeks=1)
    )
    db.session.add(policy)
    db.session.commit()

    session.pop('pending_tier', None)
    session.pop('pending_order_id', None)
    return jsonify({'success': True, 'message': 'Policy activated!'})


@user_bp.route('/claims')
@login_required
def claims():
    all_claims = Claim.query.filter_by(user_id=current_user.id).order_by(Claim.claim_date.desc()).all()
    return render_template('user/claims.html', claims=all_claims)


@user_bp.route('/payments')
@login_required
def payments():
    all_payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('user/payments.html', payments=all_payments)


@user_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        description = request.form.get('description', '').strip()
        incident_date_str = request.form.get('incident_date')
        platform_affected = request.form.get('platform_affected', current_user.platform)

        if not description or len(description) < 50:
            return jsonify({'success': False, 'message': 'Please provide a detailed description (at least 50 characters).'}), 400

        try:
            incident_date = datetime.strptime(incident_date_str, '%Y-%m-%d').date()
        except Exception:
            incident_date = date.today()

        new_report = Report(
            user_id=current_user.id,
            report_type=report_type,
            description=description,
            report_date=date.today(),
            incident_date=incident_date,
            platform_affected=platform_affected,
            status='submitted'
        )
        db.session.add(new_report)
        db.session.commit()

        # Trigger async LLM review
        try:
            from utils.llm_review import review_report_async
            review_report_async(new_report.id)
        except Exception as e:
            print(f"LLM review trigger failed: {e}")

        return jsonify({'success': True, 'message': 'Report submitted. Our team will review within 24 hours.'})

    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('user/report.html', reports=user_reports)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', current_user.full_name)
        current_user.phone = request.form.get('phone', current_user.phone)
        current_user.pincode = request.form.get('pincode', current_user.pincode)
        current_user.city = request.form.get('city', current_user.city)
        current_user.state = request.form.get('state', current_user.state)
        db.session.commit()
        return jsonify({'success': True})
    return render_template('user/profile.html')
