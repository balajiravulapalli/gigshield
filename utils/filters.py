"""
GigShield Template Filters & Context Processors
"""
import json
from datetime import datetime


def register_filters(app):
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value) if value else []
        except Exception:
            return []

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from config import Config
        return {
            'tiers': Config.INSURANCE_TIERS,
            'now': datetime.utcnow(),
            'today': datetime.utcnow().date(),
        }
