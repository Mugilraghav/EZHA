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
    DEBUG = APP_ENV == "development"
    TESTING = os.getenv("APP_ENV") == "testing"
