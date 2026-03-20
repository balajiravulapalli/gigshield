"""
GigShield Partner Portal Routes
================================
For registered delivery platforms (Zomato, Swiggy, Amazon, etc.)
to view and validate claims for their delivery agents
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Claim, Policy, DailyRecord
from datetime import date, timedelta
from sqlalchemy import func

partner_bp = Blueprint('partner', __name__)

def partner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'partner':
            flash('Partner access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@partner_bp.route('/')
@login_required
@partner_required
def dashboard():
    platform = current_user.platform  # partner's own platform e.g. 'zomato'

    # Only show claims for their delivery agents
    platform_users = User.query.filter_by(platform=platform, role='user').all()
    user_ids = [u.id for u in platform_users]

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    stats = {
        'total_agents': len(platform_users),
        'active_policies': Policy.query.filter(Policy.user_id.in_(user_ids), Policy.status == 'active').count(),
        'week_claims': Claim.query.filter(Claim.user_id.in_(user_ids), Claim.claim_date >= week_start).count(),
        'pending_verification': Claim.query.filter(
            Claim.user_id.in_(user_ids), Claim.status == 'pending').count(),
    }

    recent_claims = Claim.query.filter(
        Claim.user_id.in_(user_ids)
    ).order_by(Claim.created_at.desc()).limit(20).all()

    return render_template('partner/dashboard.html',
                           platform=platform, stats=stats, claims=recent_claims)


@partner_bp.route('/agents')
@login_required
@partner_required
def agents():
    platform = current_user.platform
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = User.query.filter_by(platform=platform, role='user')
    if search:
        query = query.filter(
            (User.full_name.ilike(f'%{search}%')) |
            (User.partner_id.ilike(f'%{search}%'))
        )
    agents = query.paginate(page=page, per_page=20)
    return render_template('partner/agents.html', agents=agents, search=search)


@partner_bp.route('/claims')
@login_required
@partner_required
def claims():
    platform = current_user.platform
    user_ids = [u.id for u in User.query.filter_by(platform=platform).all()]
    status_filter = request.args.get('status', 'all')
    query = Claim.query.filter(Claim.user_id.in_(user_ids))
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    claims = query.order_by(Claim.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int), per_page=20)
    return render_template('partner/claims.html', claims=claims, status_filter=status_filter)


@partner_bp.route('/verify-delivery', methods=['POST'])
@login_required
@partner_required
def verify_delivery():
    """
    Partner API endpoint to confirm/deny delivery activity.
    Called by partner platform to report whether agent made deliveries on a day.
    This voids insurance payout if deliveries were made.
    """
    data = request.json
    agent_partner_id = data.get('partner_agent_id')
    check_date = data.get('date')  # YYYY-MM-DD
    deliveries_made = data.get('deliveries_made', 0)

    user = User.query.filter_by(partner_id=agent_partner_id, platform=current_user.platform).first()
    if not user:
        return jsonify({'success': False, 'message': 'Agent not found'}), 404

    try:
        record_date = date.fromisoformat(check_date)
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400

    record = DailyRecord.query.filter_by(user_id=user.id, record_date=record_date).first()
    if record:
        record.delivery_verified = True
        record.deliveries_made = deliveries_made
        if deliveries_made > 0:
            record.payout_voided = True
            record.payout_amount = 0
            # Also void pending claims for this day
            claims = Claim.query.filter_by(
                user_id=user.id, claim_date=record_date, status='pending').all()
            for claim in claims:
                claim.status = 'rejected'
                claim.fraud_flags = '["delivery_made_on_claim_day"]'
        db.session.commit()

    return jsonify({'success': True, 'voided': deliveries_made > 0})
