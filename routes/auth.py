"""
GigShield Authentication Routes
================================
Handles: Register, Login, OTP Verification, 2FA, Logout
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app import db, mail
from models import User, AuditLog
from config import Config
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

# ─────────────────────────────────────────────
# HELPER: Send OTP Email
# ─────────────────────────────────────────────
def send_otp_email(user, otp):
    """Send beautifully formatted OTP email using Flask-Mail"""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: 'Georgia', serif; background: #f5f0ed; margin: 0; padding: 0; }}
        .container {{ max-width: 500px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #504746, #B6244F); padding: 32px; text-align: center; }}
        .header h1 {{ color: white; margin: 0; font-size: 28px; letter-spacing: 2px; }}
        .header p {{ color: #FBBC00; margin: 8px 0 0; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; }}
        .body {{ padding: 36px; }}
        .greeting {{ color: #504746; font-size: 16px; margin-bottom: 20px; }}
        .otp-box {{ background: linear-gradient(135deg, #504746 0%, #B89685 100%); border-radius: 12px; padding: 28px; text-align: center; margin: 24px 0; }}
        .otp-code {{ color: #FBBC00; font-size: 42px; font-weight: bold; letter-spacing: 12px; font-family: monospace; }}
        .otp-label {{ color: #BFADA3; font-size: 13px; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px; }}
        .note {{ color: #888; font-size: 13px; background: #faf8f6; padding: 16px; border-radius: 8px; border-left: 3px solid #FBBC00; }}
        .footer {{ background: #504746; padding: 20px; text-align: center; color: #BFADA3; font-size: 12px; }}
        .shield {{ font-size: 40px; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <div class="shield">🛡️</div>
          <h1>GigShield</h1>
          <p>Income Protection Platform</p>
        </div>
        <div class="body">
          <p class="greeting">Hello <strong>{user.full_name}</strong>,</p>
          <p style="color:#666;">Your one-time verification code is ready. Use it to complete your login securely.</p>
          <div class="otp-box">
            <div class="otp-code">{otp}</div>
            <div class="otp-label">One-Time Password</div>
          </div>
          <div class="note">
            ⏱️ This code expires in <strong>10 minutes</strong>.<br>
            🔒 Never share this code with anyone — GigShield will never ask for it.<br>
            ⚠️ If you didn't request this, please change your password immediately.
          </div>
        </div>
        <div class="footer">
          © {datetime.utcnow().year} GigShield · Protecting India's Gig Workers<br>
          This is an automated message. Do not reply.
        </div>
      </div>
    </body>
    </html>
    """
    msg = Message(
        subject='🛡️ Your GigShield Verification Code',
        recipients=[user.email],
        html=html_body
    )
    mail.send(msg)


def send_welcome_email(user):
    """Send welcome email after successful registration"""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: 'Georgia', serif; background: #f5f0ed; margin: 0; padding: 0; }}
        .container {{ max-width: 500px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #504746, #B6244F); padding: 32px; text-align: center; }}
        .header h1 {{ color: white; margin: 0; font-size: 28px; letter-spacing: 2px; }}
        .body {{ padding: 36px; color: #504746; }}
        .highlight {{ background: linear-gradient(135deg, #FBBC00, #B89685); border-radius: 8px; padding: 20px; margin: 20px 0; color: #504746; font-weight: bold; }}
        .footer {{ background: #504746; padding: 20px; text-align: center; color: #BFADA3; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <div style="font-size:40px;">🛡️</div>
          <h1>Welcome to GigShield!</h1>
        </div>
        <div class="body">
          <p>Dear <strong>{user.full_name}</strong>,</p>
          <p>You're now protected. GigShield has your back every time the weather or circumstances beyond your control impact your earnings.</p>
          <div class="highlight">
            ✅ Account Verified<br>
            🏍️ Platform: {user.platform.title() if user.platform else 'Not set'}<br>
            📍 Pincode: {user.pincode or 'Not set'}
          </div>
          <p>Your coverage activates the moment you subscribe to a plan. Stay safe, keep delivering.</p>
        </div>
        <div class="footer">
          © {datetime.utcnow().year} GigShield · India's Gig Worker Income Shield
        </div>
      </div>
    </body>
    </html>
    """
    msg = Message(
        subject='🛡️ Welcome to GigShield — You\'re Protected!',
        recipients=[user.email],
        html=html_body
    )
    mail.send(msg)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'partner':
            return redirect(url_for('partner.dashboard'))
        return redirect(url_for('user.dashboard'))
    return render_template('landing.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form

        # Validate required fields
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        platform = data.get('platform', '')
        partner_id = data.get('partner_id', '').strip()
        pincode = data.get('pincode', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        policy_accepted = data.get('policy_accepted') == 'true'
        policy_scrolled = data.get('policy_scrolled') == 'true'

        # Validation
        errors = []
        if not full_name: errors.append('Full name is required.')
        if not re.match(r'^[\w._%+-]+@[\w.-]+\.\w{2,}$', email): errors.append('Valid email required.')
        if not re.match(r'^\d{10}$', phone): errors.append('10-digit phone number required.')
        if len(password) < 8: errors.append('Password must be at least 8 characters.')
        if password != confirm_password: errors.append('Passwords do not match.')
        if not platform: errors.append('Please select your delivery platform.')
        if not re.match(r'^\d{6}$', pincode): errors.append('Valid 6-digit pincode required.')
        if not policy_scrolled: errors.append('Please read the entire Terms & Policy before accepting.')
        if not policy_accepted: errors.append('You must accept the Terms & Policy to register.')
        if User.query.filter_by(email=email).first(): errors.append('Email already registered.')
        if User.query.filter_by(phone=phone).first(): errors.append('Phone number already registered.')

        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        user = User(
            full_name=full_name, email=email, phone=phone,
            platform=platform, partner_id=partner_id,
            pincode=pincode, city=city, state=state,
            policy_accepted=True, policy_accepted_at=datetime.utcnow()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Send OTP for email verification
        otp = user.generate_otp()
        db.session.commit()
        try:
            send_otp_email(user, otp)
        except Exception as e:
            print(f"Mail error: {e}")

        session['pending_verify_user_id'] = user.id
        session['verify_purpose'] = 'registration'
        return jsonify({'success': True, 'redirect': url_for('auth.verify_otp_page')})

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('auth.login'))

        if not user.is_verified:
            otp = user.generate_otp()
            db.session.commit()
            try:
                send_otp_email(user, otp)
            except Exception as e:
                print(f"Mail error: {e}")
            session['pending_verify_user_id'] = user.id
            session['verify_purpose'] = 'email_verify'
            flash('Please verify your email first.', 'info')
            return redirect(url_for('auth.verify_otp_page'))

        # 2FA: always send OTP on login
        otp = user.generate_otp()
        db.session.commit()
        try:
            send_otp_email(user, otp)
        except Exception as e:
            print(f"Mail error: {e}")

        session['pending_login_user_id'] = user.id
        session['verify_purpose'] = '2fa'
        return redirect(url_for('auth.verify_otp_page'))

    return render_template('login.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_page():
    purpose = session.get('verify_purpose', '')
    if request.method == 'POST':
        otp_input = ''.join([
            request.form.get(f'otp{i}', '') for i in range(1, 7)
        ])
        user_id = session.get('pending_verify_user_id') or session.get('pending_login_user_id')
        if not user_id:
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('auth.login'))

        user = User.query.get(user_id)
        if not user or not user.verify_otp(otp_input):
            flash('Invalid or expired OTP. Please try again.', 'error')
            return redirect(url_for('auth.verify_otp_page'))

        user.otp_secret = None
        user.otp_expires_at = None

        if purpose in ('registration', 'email_verify'):
            user.is_verified = True
            db.session.commit()
            session.pop('pending_verify_user_id', None)
            session.pop('verify_purpose', None)
            try:
                send_welcome_email(user)
            except Exception:
                pass
            login_user(user)
            flash('Email verified! Welcome to GigShield.', 'success')
            return redirect(url_for('user.dashboard'))
        elif purpose == '2fa':
            db.session.commit()
            session.pop('pending_login_user_id', None)
            session.pop('verify_purpose', None)
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'partner':
                return redirect(url_for('partner.dashboard'))
            return redirect(url_for('user.dashboard'))

    return render_template('verify_otp.html', purpose=purpose)


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    user_id = session.get('pending_verify_user_id') or session.get('pending_login_user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired'}), 400
    user = User.query.get(user_id)
    otp = user.generate_otp()
    db.session.commit()
    try:
        send_otp_email(user, otp)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))
