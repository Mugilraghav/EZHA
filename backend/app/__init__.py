import os
from flask import Flask

from .config import Config
from .auth import auth_service
from .database import initialize_database
from .models.catalog import get_demo_catalog
from .routes import admin_bp, artisan_bp, auth_bp, customers_bp, public_api_bp, public_bp, vendors_bp


def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "..", "frontend"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)
    if app.config.get("APP_ENV") == "production":
        jwt_secret = app.config.get("JWT_SECRET_KEY") or app.config.get("SECRET_KEY")
        if not jwt_secret or len(jwt_secret) < 32 or jwt_secret in {"dev-secret-key", "replace_with_secure_secret"}:
            raise RuntimeError("Set JWT_SECRET to a random value of at least 32 characters before production startup")
    initialize_database(app)
    app.config["EZHA_CATALOG"] = get_demo_catalog()
    app.config.setdefault("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)
    app.extensions["ezha_bookings"] = []
    app.extensions["ezha_portfolio"] = []
    app.extensions["ezha_auth_service"] = auth_service
    app.register_blueprint(public_bp)
    app.register_blueprint(public_api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(artisan_bp)
    app.register_blueprint(admin_bp)
    return app
