from .admin import bp as admin_bp
from .artisan import bp as artisan_bp
from .auth import bp as auth_bp
from .customers import bp as customers_bp
from .public import public_bp
from .public_api import bp as public_api_bp
from .vendors import bp as vendors_bp

__all__ = ["public_bp", "public_api_bp", "auth_bp", "customers_bp", "vendors_bp", "admin_bp", "artisan_bp"]
