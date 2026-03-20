"""
GigShield - AI-Powered Parametric Insurance Platform
=====================================================
Main Flask Application Entry Point

API KEY CONFIGURATION GUIDE:
All API keys are loaded from environment variables or config.py
See config.py for full documentation on each key.
"""

from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.admin import admin_bp
    from routes.partner import partner_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp, url_prefix='/dashboard')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(partner_bp, url_prefix='/partner')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register template filters and context processors
    from utils.filters import register_filters
    register_filters(app)

    with app.app_context():
        db.create_all()

    # Start scheduler (uncomment in production)
    # from routes.api import setup_scheduler
    # setup_scheduler(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
