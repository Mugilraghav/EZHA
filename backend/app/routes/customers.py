from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from backend.app.auth import auth_service
from backend.app.models.user import ArtisanProfile, CustomerNotification, CustomerProfile, User
from backend.app.services.artisan_calendar import artisan_month_availability, slot_is_available
from backend.app.services.booking_lifecycle import process_expired_acceptance_deadlines
from backend.app.services.customer_catalog import query_customer_works

bp = Blueprint("customers", __name__, url_prefix="/api/v1/customers")
service = auth_service
WORK_CATEGORIES = {"MAKEUP", "MEHENDI", "DRESS", "FULL_PACKAGE"}


def _customer_claims():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401)
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return None, (jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401)
    if claims.get("role") != "CUSTOMER":
        return None, (jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403)
    return claims, None


def _serialize_customer_profile(profile: CustomerProfile | None) -> dict:
    if profile is None:
        return {
            "phone": "",
            "address_line1": "",
            "address_line2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "has_address": False,
        }
    return {
        "phone": profile.phone,
        "address_line1": profile.address_line1,
        "address_line2": profile.address_line2,
        "city": profile.city,
        "state": profile.state,
        "pincode": profile.pincode,
        "has_address": bool(profile.address_line1 and profile.city and profile.pincode),
    }


@bp.get("/me")
def customer_profile():
    claims, error = _customer_claims()
    if error:
        return error

    with current_app.extensions["ezha_session_factory"]() as session:
        profile = session.get(CustomerProfile, claims["sub"])
    return jsonify({
        "success": True,
        "data": {
            "role": claims["role"],
            "email": claims["email"],
            "name": claims["name"],
            "profile": _serialize_customer_profile(profile),
        },
        "message": "Customer profile loaded",
    }), 200


@bp.patch("/me")
def update_customer_profile():
    claims, error = _customer_claims()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    pincode = str(payload.get("pincode", "")).strip()
    if pincode and (not pincode.isdigit() or len(pincode) != 6):
        return jsonify({"success": False, "error": {"code": "INVALID_PINCODE", "message": "Enter a valid 6-digit PIN code"}}), 400

    with current_app.extensions["ezha_session_factory"].begin() as session:
        profile = session.get(CustomerProfile, claims["sub"])
        if profile is None:
            profile = CustomerProfile(customer_id=claims["sub"])
            session.add(profile)
        profile.phone = str(payload.get("phone", profile.phone)).strip()[:20]
        profile.address_line1 = str(payload.get("address_line1", profile.address_line1)).strip()[:200]
        profile.address_line2 = str(payload.get("address_line2", profile.address_line2)).strip()[:200]
        profile.city = str(payload.get("city", profile.city)).strip()[:100]
        profile.state = str(payload.get("state", profile.state)).strip()[:100]
        profile.pincode = pincode[:10] or profile.pincode

    return jsonify({"success": True, "data": {"profile": _serialize_customer_profile(profile)}, "message": "Doorstep address saved"}), 200


@bp.get("/cities")
def list_service_cities():
    claims, error = _customer_claims()
    if error:
        return error
    with current_app.extensions["ezha_session_factory"]() as session:
        rows = session.scalars(
            select(ArtisanProfile.city)
            .join(User, User.id == ArtisanProfile.artisan_id)
            .where(User.role == "ARTISAN", ArtisanProfile.city != "")
        ).all()
    cities = sorted({city.strip() for city in rows if city and city.strip()}, key=str.casefold)
    return jsonify({"success": True, "data": {"cities": cities}}), 200


@bp.get("/works")
def list_works():
    claims, error = _customer_claims()
    if error:
        return error
    category = request.args.get("category", "").strip().upper()
    city = request.args.get("city", "").strip()
    search = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = min(48, max(4, int(request.args.get("per_page", 8) or 8)))
    if category and category not in WORK_CATEGORIES:
        return jsonify({"success": False, "error": {"code": "INVALID_CATEGORY", "message": "Choose makeup, mehendi, dress, or full package"}}), 400

    with current_app.extensions["ezha_session_factory"]() as session:
        process_expired_acceptance_deadlines(session)
        session.commit()
        works = query_customer_works(session, category=category, city=city, search=search)
    total = len(works)
    start = (page - 1) * per_page
    page_items = works[start : start + per_page]
    return jsonify({
        "success": True,
        "data": {
            "works": page_items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        },
    }), 200


@bp.get("/notifications")
def customer_notifications():
    claims, error = _customer_claims()
    if error:
        return error
    with current_app.extensions["ezha_session_factory"]() as session:
        process_expired_acceptance_deadlines(session)
        notes = session.scalars(
            select(CustomerNotification)
            .where(CustomerNotification.customer_id == claims["sub"])
            .order_by(CustomerNotification.created_at.desc())
            .limit(30)
        ).all()
        session.commit()
    return jsonify({
        "success": True,
        "data": {
            "notifications": [{
                "id": note.id,
                "kind": note.kind,
                "title": note.title,
                "message": note.message,
                "booking_id": note.booking_id,
                "is_read": note.is_read,
                "created_at": note.created_at.isoformat(),
            } for note in notes],
        },
    }), 200


@bp.get("/artisans/<artisan_id>/calendar")
def artisan_calendar(artisan_id):
    claims, error = _customer_claims()
    if error:
        return error
    year = int(request.args.get("year", 0) or 0)
    month = int(request.args.get("month", 0) or 0)
    if not year or not month:
        from datetime import datetime

        now = datetime.now()
        year, month = now.year, now.month
    with current_app.extensions["ezha_session_factory"]() as session:
        artisan = session.scalar(select(User).where(User.id == artisan_id, User.role == "ARTISAN"))
        if not artisan:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Artisan not found"}}), 404
        data = artisan_month_availability(session, artisan_id, year, month)
    return jsonify({"success": True, "data": data}), 200


@bp.get("/artisans/<artisan_id>/slot-check")
def artisan_slot_check(artisan_id):
    claims, error = _customer_claims()
    if error:
        return error
    service_date = request.args.get("date", "").strip()
    service_time = request.args.get("time", "").strip()
    if not service_date or not service_time:
        return jsonify({"success": False, "error": {"code": "MISSING_SCHEDULE", "message": "Date and time are required"}}), 400
    with current_app.extensions["ezha_session_factory"]() as session:
        available = slot_is_available(session, artisan_id, service_date, service_time)
    return jsonify({"success": True, "data": {"available": available}}), 200


@bp.get("/artisans")
def list_artisans():
    claims, error = _customer_claims()
    if error:
        return error

    category = request.args.get("category", "").strip().upper()
    city = request.args.get("city", "").strip().casefold()
    if category and category not in WORK_CATEGORIES:
        return jsonify({"success": False, "error": {"code": "INVALID_CATEGORY", "message": "Choose makeup, mehendi, dress, or full package"}}), 400

    with current_app.extensions["ezha_session_factory"]() as session:
        flat_works = query_customer_works(session, category=category, city=city)
        artisans_map = {}
        for work in flat_works:
            aid = work["artisan_id"]
            if aid not in artisans_map:
                artisans_map[aid] = {
                    "id": aid,
                    "username": work["artisan_username"],
                    "name": work["artisan_name"],
                    "city": work["artisan_city"],
                    "category": work["category"],
                    "works": [],
                }
            artisans_map[aid]["works"].append({
                "id": work["id"],
                "title": work["title"],
                "category": work["category"],
                "price": work["price"],
                "caption": work["caption"],
                "image_url": work["image_url"],
            })
    return jsonify({"success": True, "data": {"artisans": list(artisans_map.values())}}), 200
