"""
GigShield LLM Report Review
============================
Uses Anthropic Claude API to auto-review user-submitted reports.
Checks policy compliance, weather data, and downdetector status.

>>> ANTHROPIC_API_KEY is set in config.py
"""

import json
import requests
from datetime import date
from flask import current_app


def review_report_async(report_id: int):
    """
    Trigger LLM review of a submitted report.
    Called async after report submission.
    """
    from app import db
    from models import Report, User, Policy, WeatherLog

    report = Report.query.get(report_id)
    if not report:
        return

    user = User.query.get(report.user_id)
    policy = Policy.query.filter_by(user_id=report.user_id, status='active').first()

    # Gather evidence
    weather_on_day = WeatherLog.query.filter_by(
        pincode=user.pincode, log_date=report.incident_date
    ).first()

    # Check Downdetector for app crashes
    app_down = False
    if report.report_type == 'app_crash':
        app_down = check_downdetector(report.platform_affected or user.platform or 'zomato')

    # Build context for LLM
    context = {
        'user_name': user.full_name,
        'platform': user.platform,
        'incident_date': str(report.incident_date),
        'report_type': report.report_type,
        'description': report.description,
        'has_active_policy': policy is not None,
        'policy_tier': policy.tier if policy else None,
        'weather_disruption_logged': weather_on_day is not None and weather_on_day.disruption_triggered,
        'weather_type': weather_on_day.disruption_type if weather_on_day else None,
        'platform_outage_detected': app_down,
    }

    verdict, confidence, analysis = call_llm_review(context)

    report.llm_review = analysis
    report.llm_verdict = verdict
    report.llm_confidence = confidence
    if verdict == 'valid':
        report.status = 'under_review'
    db.session.commit()


def call_llm_review(context: dict) -> tuple:
    """
    Calls Anthropic API to review a claim report.
    Returns: (verdict, confidence, analysis_text)

    >>> ANTHROPIC_API_KEY from config.py
    """
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    if not api_key or 'YOUR_' in api_key:
        return _mock_llm_review(context)

    system_prompt = """You are GigShield's AI Claims Auditor. You review disputed insurance claims from 
delivery workers in India. Your job is to assess whether a claim is valid based on:
1. The GigShield policy terms (income loss due to weather/social disruptions ONLY — no health, vehicle, or accident coverage)
2. Actual weather data logs provided
3. Platform downtime reports
4. The worker's description consistency

You MUST be fair but conservative — only recommend 'valid' if there is clear evidence. 
Respond in JSON only: {"verdict": "valid|invalid|needs_review", "confidence": 0.0-1.0, "analysis": "brief explanation"}"""

    user_message = f"""Review this GigShield insurance claim report:

Context:
{json.dumps(context, indent=2)}

Is this a valid claim for income loss payout? Apply GigShield policy strictly."""

    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 500,
                'system': system_prompt,
                'messages': [{'role': 'user', 'content': user_message}]
            },
            timeout=30
        )
        data = resp.json()
        text = data['content'][0]['text']
        parsed = json.loads(text)
        return parsed.get('verdict', 'needs_review'), parsed.get('confidence', 0.5), parsed.get('analysis', '')
    except Exception as e:
        print(f"LLM review error: {e}")
        return 'needs_review', 0.5, f'Automated review unavailable: {str(e)}'


def check_downdetector(platform: str) -> bool:
    """
    Check if a platform had a reported outage via Downdetector India.
    Basic scraping approach — no official API.

    >>> DOWNDETECTOR_BASE_URL from config.py
    """
    platform_slugs = {
        'zomato': 'zomato', 'swiggy': 'swiggy', 'amazon': 'amazon',
        'flipkart': 'flipkart', 'zepto': 'zepto', 'blinkit': 'blinkit',
        'dunzo': 'dunzo'
    }
    slug = platform_slugs.get(platform.lower(), platform.lower())
    url = f"https://downdetector.in/status/{slug}/"

    try:
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        # Look for "problems" indicators in the response
        text = resp.text.lower()
        indicators = ['problems at', 'outage', 'disruption', 'issues']
        return any(ind in text for ind in indicators)
    except Exception:
        return False


def _mock_llm_review(context: dict) -> tuple:
    """Fallback when LLM not configured"""
    if context.get('weather_disruption_logged') or context.get('platform_outage_detected'):
        return 'valid', 0.72, 'Weather disruption or platform outage confirmed. Claim appears valid based on available evidence.'
    return 'needs_review', 0.5, 'Insufficient automated evidence. Manual review recommended.'
