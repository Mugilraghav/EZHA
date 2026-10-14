import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key")
    JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET", "dev-refresh-secret")
    APP_ENV = os.getenv("APP_ENV", "development")
    SEED_DEMO_USERS = os.getenv("SEED_DEMO_USERS", "false" if APP_ENV == "production" else "true").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'ezha.db'}")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "portfolio"))
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    PLATFORM_COMMISSION_RATE = float(os.getenv("PLATFORM_COMMISSION_RATE", "0.15"))
    LANDING_HERO_PATH = os.getenv("LANDING_HERO_PATH", "")
    FOUNDER_IMAGE_PATH = os.getenv("FOUNDER_IMAGE_PATH", "")
    FOUNDER_NAME = os.getenv("FOUNDER_NAME", "Mugilraghav")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "vimala8121983@gmail.com")
    PORTFOLIO_LISTING_BUFFER_MINUTES = int(os.getenv("PORTFOLIO_LISTING_BUFFER_MINUTES", "15"))
    ORDER_ACCEPTANCE_HOURS = int(os.getenv("ORDER_ACCEPTANCE_HOURS", "3"))
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true")
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
    DEBUG = APP_ENV == "development"
    TESTING = os.getenv("APP_ENV") == "testing"
