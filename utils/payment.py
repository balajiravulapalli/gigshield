"""
GigShield Payment Utility
==========================
Razorpay integration for premium collection and payout simulation.

>>> RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are set in config.py
"""

import hmac
import hashlib
import json
from flask import current_app

def _get_razorpay_client():
    """
    >>> Returns configured Razorpay client
    >>> RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET from config.py
    """
    try:
        import razorpay
        key_id = current_app.config['RAZORPAY_KEY_ID']
        key_secret = current_app.config['RAZORPAY_KEY_SECRET']
        if 'YOUR_' in key_id or 'rzp_test_YOUR' in key_id:
            return None  # Not configured yet
        return razorpay.Client(auth=(key_id, key_secret))
    except ImportError:
        return None


def create_razorpay_order(amount: float, receipt: str, notes: dict = None):
    """
    Create a Razorpay order for premium payment.
    amount: INR amount (not paise)
    """
    client = _get_razorpay_client()
    if not client:
        # Mock order for development
        return {
            'id': f'mock_order_{receipt}',
            'amount': int(amount * 100),
            'currency': 'INR',
            'receipt': receipt,
            '_mock': True
        }

    order_data = {
        'amount': int(amount * 100),  # Razorpay uses paise
        'currency': 'INR',
        'receipt': receipt,
        'notes': notes or {}
    }
    return client.order.create(data=order_data)


def verify_razorpay_payment(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay payment signature for security"""
    if order_id.startswith('mock_order_'):
        return True  # Allow mock orders in dev

    key_secret = current_app.config['RAZORPAY_KEY_SECRET']
    if 'YOUR_' in key_secret:
        return True  # Dev bypass

    try:
        body = f"{order_id}|{payment_id}"
        generated_signature = hmac.new(
            key_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(generated_signature, signature)
    except Exception:
        return False


def initiate_payout(user, amount: float, description: str):
    """
    Simulate payout to delivery agent.
    In production: use Razorpay Payouts API or UPI transfer.

    >>> Replace mock with actual Razorpay Payout or bank transfer here
    """
    client = _get_razorpay_client()
    if not client:
        # Mock payout
        return {
            'id': f'mock_payout_{user.id}_{amount}',
            'status': 'processed',
            'amount': int(amount * 100),
            '_mock': True
        }

    # >>> PRODUCTION PAYOUT: Razorpay Payouts API
    # Requires activated Razorpay account with payout feature
    # payout_data = {
    #     'account_number': 'YOUR_RAZORPAY_X_ACCOUNT',  # >>> INSERT RAZORPAY X ACCOUNT
    #     'amount': int(amount * 100),
    #     'currency': 'INR',
    #     'mode': 'UPI',
    #     'purpose': 'payout',
    #     'fund_account': {
    #         'account_type': 'vpa',
    #         'vpa': {'address': user.upi_id},
    #         'contact': {'name': user.full_name, 'email': user.email, 'contact': user.phone, 'type': 'employee'}
    #     },
    #     'notes': {'description': description}
    # }
    # return client.payout.create(data=payout_data)

    return {'id': f'mock_payout_{user.id}', 'status': 'queued', '_mock': True}
