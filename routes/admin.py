"""
GigShield Admin Routes
=======================
Full admin portal: users, claims, payouts, fraud, analytics
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Policy, Claim, Payment, Report, WeatherLog, DailyRecord, AuditLog
from datetime import datetime, date, timedelta
from sqlalchemy import func
import json

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    stats = {
        'total_users': User.query.filter_by(role='user').count(),
        'active_policies': Policy.query.filter_by(status='active').count(),
        'pending_claims': Claim.query.filter_by(status='pending').count(),
        'today_payouts': db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_type == 'payout',
            Payment.status == 'completed',
            func.date(Payment.created_at) == today
        ).scalar() or 0,
        'week_premium': db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_type == 'premium',
            Payment.status == 'completed',
            Payment.created_at >= week_start
        ).scalar() or 0,
        'fraud_flagged': Claim.query.filter(Claim.fraud_score >= 0.6).count(),
        'pending_reports': Report.query.filter_by(status='submitted').count(),
    }

    recent_claims = Claim.query.order_by(Claim.created_at.desc()).limit(10).all()
    recent_reports = Report.query.filter_by(status='submitted').order_by(Report.created_at.desc()).limit(5).all()

    # Weekly payout chart data (last 4 weeks)
    chart_data = []
    for i in range(4):
        wk_start = today - timedelta(weeks=i+1, days=today.weekday())
        wk_end = wk_start + timedelta(days=6)
        payout = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_type == 'payout',
            Payment.status == 'completed',
            Payment.created_at >= wk_start,
            Payment.created_at <= wk_end
        ).scalar() or 0
        premium = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_type == 'premium',
            Payment.status == 'completed',
            Payment.created_at >= wk_start,
            Payment.created_at <= wk_end
        ).scalar() or 0
        chart_data.append({'week': f'W-{i+1}', 'payout': float(payout), 'premium': float(premium)})

    chart_data.reverse()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_claims=recent_claims, recent_reports=recent_reports,
                           chart_data=json.dumps(chart_data))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = User.query.filter_by(role='user')
    if search:
        query = query.filter(
            (User.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.phone.ilike(f'%{search}%'))
        )
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    policies = Policy.query.filter_by(user_id=user_id).all()
    claims = Claim.query.filter_by(user_id=user_id).order_by(Claim.created_at.desc()).all()
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    return render_template('admin/user_detail.html', user=user, policies=policies,
                           claims=claims, payments=payments)


@admin_bp.route('/claims')
@login_required
@admin_required
def claims():
    status_filter = request.args.get('status', 'all')
    query = Claim.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    claims = query.order_by(Claim.created_at.desc()).paginate(page=request.args.get('page', 1, type=int), per_page=20)
    return render_template('admin/claims.html', claims=claims, status_filter=status_filter)


@admin_bp.route('/claims/<int:claim_id>/action', methods=['POST'])
@login_required
@admin_required
def claim_action(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    action = request.json.get('action')  # approve | reject
    notes = request.json.get('notes', '')

    if action == 'approve':
        claim.status = 'approved'
        claim.processed_at = datetime.utcnow()
        # Create payout
        payment = Payment(
            user_id=claim.user_id,
            payment_type='payout',
            amount=claim.payout_amount,
            status='pending',
            description=f'Claim payout - {claim.disruption_type}',
            week_start=date.today() - timedelta(days=date.today().weekday())
        )
        db.session.add(payment)
        db.session.commit()
        claim.payment_id = payment.id
        db.session.commit()
    elif action == 'reject':
        claim.status = 'rejected'
        claim.processed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    reports = Report.query.order_by(Report.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int), per_page=20)
    return render_template('admin/reports.html', reports=reports)


@admin_bp.route('/reports/<int:report_id>/review', methods=['GET', 'POST'])
@login_required
@admin_required
def report_review(report_id):
    report = Report.query.get_or_404(report_id)
    if request.method == 'POST':
        decision = request.form.get('decision')
        notes = request.form.get('admin_notes', '')
        payout_amount = float(request.form.get('payout_amount', 0))
        report.admin_decision = decision
        report.admin_notes = notes
        report.status = 'resolved'
        report.resolved_at = datetime.utcnow()
        if decision == 'approved' and payout_amount > 0:
            report.payout_triggered = True
            report.payout_amount = payout_amount
            payment = Payment(
                user_id=report.user_id,
                payment_type='payout',
                amount=payout_amount,
                status='pending',
                description=f'Report #{report_id} Payout'
            )
            db.session.add(payment)
        db.session.commit()
        flash('Report resolved.', 'success')
        return redirect(url_for('admin.reports'))
    return render_template('admin/report_review.html', report=report)


@admin_bp.route('/payouts')
@login_required
@admin_required
def payouts():
    payouts = Payment.query.filter_by(payment_type='payout').order_by(
        Payment.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int), per_page=20)
    return render_template('admin/payouts.html', payouts=payouts)


@admin_bp.route('/fraud')
@login_required
@admin_required
def fraud():
    flagged = Claim.query.filter(Claim.fraud_score >= 0.6).order_by(
        Claim.fraud_score.desc()).all()
    return render_template('admin/fraud.html', flagged=flagged)


@admin_bp.route('/weather-logs')
@login_required
@admin_required
def weather_logs():
    logs = WeatherLog.query.order_by(WeatherLog.log_time.desc()).limit(100).all()
    return render_template('admin/weather_logs.html', logs=logs)
