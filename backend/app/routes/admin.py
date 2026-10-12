from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from backend.app.auth import auth_service
from backend.app.models.user import ArtisanProfile, Booking, PortfolioWork, User

bp = Blueprint("admin", __name__, url_prefix="/api/v1")
service = auth_service


@bp.get("/admin/dashboard")
def admin_dashboard():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401

    token = auth_header.split(" ", 1)[1].strip()
    claims = service.verify_token(token, "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401

    if claims.get("role") != "ADMIN":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin access required"}}), 403

    user_counts = service.user_counts()
    customers = user_counts.get("CUSTOMER", 0)
    artisans = user_counts.get("ARTISAN", 0)
    demo_orders = ([
        {"id": "ord_2001", "customer": "Meera S.", "service": "Bridal Makeup Trial", "date": "2026-11-15", "status": "CONFIRMED", "amount": 8500},
        {"id": "ord_2002", "customer": "Rhea K.", "service": "Bridal Makeup Trial", "date": "2026-11-18", "status": "PENDING", "amount": 8500},
    ] if current_app.config.get("APP_ENV", "development") != "production" else [])
    with current_app.extensions["ezha_session_factory"]() as session:
        booking_rows = session.execute(
            select(Booking, PortfolioWork, User)
            .join(PortfolioWork, PortfolioWork.id == Booking.work_id)
            .join(User, User.id == Booking.customer_id)
            .order_by(Booking.created_at.desc())
        ).all()
        persisted_orders = [{
            "id": booking.id,
            "customer": customer.name,
            "service": work.title,
            "date": booking.service_date,
            "status": booking.status,
            "amount": booking.amount,
            "payment_status": booking.payment_status,
        } for booking, work, customer in booking_rows]
        artisan_rows = session.execute(
            select(User, ArtisanProfile)
            .join(ArtisanProfile, ArtisanProfile.artisan_id == User.id)
            .where(User.role == "ARTISAN")
            .order_by(User.created_at.desc())
        ).all()
        artisan_list = [{
            "id": artisan.id,
            "name": artisan.name,
            "username": artisan.username,
            "city": profile.city,
            "category": profile.category,
        } for artisan, profile in artisan_rows]
    orders = demo_orders + persisted_orders
    data = {
        "kpis": {
            "customers": customers,
            "artisans": artisans,
            "orders": len(orders),
            "revenue": sum(order["amount"] for order in orders if order["status"] == "CONFIRMED"),
        },
        "recent_orders": orders[-10:][::-1],
        "vendors": current_app.config["EZHA_CATALOG"]["vendors"],
        "artisan_list": artisan_list,
    }
    return jsonify({"success": True, "data": data, "message": "Admin dashboard loaded"}), 200
