"""
GigShield Fraud Detection
==========================
Intelligent fraud scoring for insurance claims.

╔══════════════════════════════════════════════════════════════════════════╗
║  >>> HUGGING FACE MODEL INSERTION POINT                                  ║
║  Search for: # ===== HF MODEL INSERTION POINT =====                     ║
║  Replace the rule-based scorer with your trained HuggingFace model.     ║
║  Recommended: a binary classification model trained on claim patterns.  ║
║  HUGGINGFACE_API_KEY and FRAUD_MODEL_ENDPOINT are set in config.py      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
from datetime import date, timedelta
from flask import current_app


def calculate_fraud_score(user, claim_date: date, disruption_type: str,
                          payout_amount: float, pincode: str) -> dict:
    """
    Returns:
        score: float 0.0–1.0 (higher = more suspicious)
        flags: list of string flag descriptions
        verdict: 'clean' | 'suspicious' | 'high_risk'
    """

    # ===== HF MODEL INSERTION POINT =====
    # To replace with your HuggingFace model:
    # 1. Prepare feature vector from the inputs below
    # 2. Call your inference endpoint (see _call_hf_model below)
    # 3. Return the model's fraud probability score
    # 4. Comment out or remove the rule_based_fraud_score call below
    #
    # Example:
    #   features = _build_feature_vector(user, claim_date, disruption_type, payout_amount, pincode)
    #   hf_score = _call_hf_model(features)
    #   return {'score': hf_score, 'flags': [], 'verdict': _verdict(hf_score)}
    # ===== END HF MODEL INSERTION POINT =====

    return _rule_based_fraud_score(user, claim_date, disruption_type, payout_amount, pincode)


def _call_hf_model(features: dict) -> float:
    """
    >>> HuggingFace Inference API call
    >>> Set HUGGINGFACE_API_KEY and FRAUD_MODEL_ENDPOINT in config.py

    features: dict of numerical/categorical claim features
    Returns: fraud probability float 0-1
    """
    api_key = current_app.config.get('HUGGINGFACE_API_KEY', '')
    model_endpoint = current_app.config.get('FRAUD_MODEL_ENDPOINT', '')

    if not api_key or 'YOUR_' in api_key or not model_endpoint or 'YOUR_' in model_endpoint:
        # HF model not configured — fallback to rule-based
        return None

    url = f"https://api-inference.huggingface.co/models/{model_endpoint}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.post(url, headers=headers, json={"inputs": features}, timeout=10)
        result = resp.json()
        # Parse response based on your model output format:
        # For binary classifier: result[0]['score'] if result[0]['label'] == 'FRAUD' else 1 - result[0]['score']
        if isinstance(result, list) and result:
            return float(result[0].get('score', 0.5))
        return 0.5
    except Exception as e:
        print(f"HF model call failed: {e}")
        return None


def _rule_based_fraud_score(user, claim_date: date, disruption_type: str,
                             payout_amount: float, pincode: str) -> dict:
    """
    Fallback rule-based fraud detection when ML model not available.
    Used until HuggingFace model is integrated.
    """
    from models import Claim, DailyRecord, WeatherLog
    from app import db

    score = 0.0
    flags = []

    # 1. Frequency check — too many claims in short period
    claims_last_30 = Claim.query.filter(
        Claim.user_id == user.id,
        Claim.claim_date >= claim_date - timedelta(days=30),
        Claim.status != 'rejected'
    ).count()
    if claims_last_30 >= 5:
        score += 0.3
        flags.append(f'High claim frequency: {claims_last_30} claims in 30 days')

    # 2. Weather validation — did a weather disruption actually occur?
    weather_log = WeatherLog.query.filter_by(
        pincode=pincode, log_date=claim_date, disruption_triggered=True
    ).first()
    if not weather_log:
        score += 0.4
        flags.append('No weather disruption record found for this pincode on claim date')

    # 3. Delivery check — did partner API show deliveries made?
    daily = DailyRecord.query.filter_by(user_id=user.id, record_date=claim_date).first()
    if daily and daily.deliveries_made > 0:
        score += 0.5
        flags.append(f'Partner API shows {daily.deliveries_made} deliveries on claimed disruption day')

    # 4. Duplicate claim check
    duplicate = Claim.query.filter_by(
        user_id=user.id, claim_date=claim_date
    ).first()
    if duplicate:
        score += 0.3
        flags.append('Duplicate claim for same date already exists')

    # 5. New account with high claim
    from datetime import datetime
    account_age_days = (datetime.utcnow() - user.created_at).days
    if account_age_days < 14 and payout_amount > 500:
        score += 0.2
        flags.append(f'New account ({account_age_days} days old) with high payout claim')

    # 6. Weekend / holiday spike pattern (basic heuristic)
    if claim_date.weekday() in (5, 6):  # Saturday/Sunday
        score += 0.05
        flags.append('Claim on weekend — verify platform downtime')

    score = min(score, 1.0)
    verdict = 'clean' if score < 0.3 else ('suspicious' if score < 0.6 else 'high_risk')
    return {'score': round(score, 3), 'flags': flags, 'verdict': verdict}


def _build_feature_vector(user, claim_date, disruption_type, payout_amount, pincode):
    """Build numeric feature dict for ML model input"""
    from models import Claim
    from datetime import datetime
    return {
        'account_age_days': (datetime.utcnow() - user.created_at).days,
        'claims_30_days': Claim.query.filter(
            Claim.user_id == user.id,
            Claim.claim_date >= claim_date - timedelta(days=30)
        ).count(),
        'payout_amount': payout_amount,
        'day_of_week': claim_date.weekday(),
        'disruption_type': disruption_type,
    }


def _verdict(score: float) -> str:
    return 'clean' if score < 0.3 else ('suspicious' if score < 0.6 else 'high_risk')
