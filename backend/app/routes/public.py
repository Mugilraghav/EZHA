import os

from flask import Blueprint, redirect, send_from_directory

public_bp = Blueprint("public", __name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend")
PAGES_DIR = os.path.join(FRONTEND_DIR, "pages")
VENDOR_DIR = os.path.join(FRONTEND_DIR, "vendor")
ADMIN_DIR = os.path.join(FRONTEND_DIR, "admin")
CUSTOMER_DIR = os.path.join(FRONTEND_DIR, "customer")
AUTH_DIR = os.path.join(FRONTEND_DIR, "pages", "auth")


@public_bp.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@public_bp.get("/login")
def login_page():
    return send_from_directory(AUTH_DIR, "login.html")


@public_bp.get("/register")
def register_page():
    return send_from_directory(AUTH_DIR, "register.html")


@public_bp.get("/portal")
def portal_redirect():
    return redirect("/login")


@public_bp.get("/customer/services")
def customer_services():
    return send_from_directory(CUSTOMER_DIR, "services.html")


@public_bp.get("/customer/cart")
def customer_cart():
    return send_from_directory(CUSTOMER_DIR, "cart.html")


@public_bp.get("/explore")
def explore():
    return redirect("/#vision")


@public_bp.get("/category")
def category():
    return send_from_directory(PAGES_DIR, "category.html")


@public_bp.get("/vendor")
def vendor():
    return send_from_directory(PAGES_DIR, "vendor.html")


@public_bp.get("/service")
def service():
    return send_from_directory(PAGES_DIR, "service.html")


@public_bp.get("/booking")
def booking():
    return send_from_directory(PAGES_DIR, "booking.html")


@public_bp.get("/checkout")
def checkout():
    return send_from_directory(PAGES_DIR, "checkout.html")


@public_bp.get("/vendor/dashboard")
def vendor_dashboard():
    return send_from_directory(VENDOR_DIR, "dashboard.html")


@public_bp.get("/artisan/dashboard")
def artisan_dashboard():
    return send_from_directory(VENDOR_DIR, "dashboard.html")


@public_bp.get("/admin/dashboard")
def admin_dashboard():
    return send_from_directory(ADMIN_DIR, "dashboard.html")


@public_bp.get("/health")
def health():
    return {"status": "ok", "service": "EZHA"}, 200
