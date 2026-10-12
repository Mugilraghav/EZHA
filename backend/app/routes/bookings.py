from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.app.auth import SimpleAuthService
from backend.app.models.catalog import get_demo_catalog

bp = Blueprint("bookings", __name__, url_prefix="/api/v1")
service = SimpleAuthService()


@bp.post("/bookings")
def create_booking():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401

    token = auth_header.split(" ", 1)[1].strip()
    claims = service.verify_token(token, "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401

    payload = request.get_json(silent=True) or {}
    vendor_id = payload.get("vendor_id")
    service_id = payload.get("service_id")
    booking_date = payload.get("date")
    booking_time = payload.get("time")
    guest_count = payload.get("guest_count", 1)

    if not vendor_id or not service_id or not booking_date or not booking_time:
        return jsonify({"success": False, "error": {"code": "INVALID_BOOKING", "message": "vendor_id, service_id, date, and time are required"}}), 400

    catalog = get_demo_catalog()
    vendor = next((item for item in catalog["vendors"] if item["id"] == vendor_id), None)
    booking_service = next((item for item in catalog["services"] if item["id"] == service_id), None)

    if not vendor:
        return jsonify({"success": False, "error": {"code": "VENDOR_NOT_FOUND", "message": "Vendor not found"}}), 404
    if not booking_service:
        return jsonify({"success": False, "error": {"code": "SERVICE_NOT_FOUND", "message": "Service not found"}}), 404

    booking = {
        "id": f"booking_{len(catalog['services']) + 1}",
        "customer_email": claims.get("email"),
        "vendor_id": vendor_id,
        "service_id": service_id,
        "vendor_name": vendor["name"],
        "service_title": booking_service["title"],
        "date": booking_date,
        "time": booking_time,
        "guest_count": guest_count,
        "notes": payload.get("notes", ""),
        "status": "pending",
        "total_price": booking_service["price"],
    }
    return jsonify({"success": True, "data": booking, "message": "Booking created successfully"}), 201
