from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from backend.app.auth import auth_service
from backend.app.models.user import ArtisanProfile, CustomerProfile, PortfolioWork, User
from backend.app.services.storage import portfolio_image_url

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
        rows = session.execute(
            select(User, ArtisanProfile).join(ArtisanProfile, ArtisanProfile.artisan_id == User.id).where(User.role == "ARTISAN").order_by(User.created_at.desc())
        ).all()
        artisans = []
        for artisan, profile in rows:
            if city and profile.city.casefold() != city:
                continue
            works_query = select(PortfolioWork).where(PortfolioWork.artisan_id == artisan.id)
            if category:
                works_query = works_query.where(PortfolioWork.category == category)
            works = session.scalars(works_query.order_by(PortfolioWork.created_at.desc())).all()
            if category and not works:
                continue
            artisans.append({
                "id": artisan.id,
                "username": artisan.username,
                "name": artisan.name,
                "city": profile.city,
                "category": profile.category,
                "works": [{
                    "id": work.id,
                    "title": work.title,
                    "category": work.category,
                    "price": work.price,
                    "caption": work.caption,
                    "image_url": portfolio_image_url(work.filename, work.storage_provider),
                } for work in works],
            })
    return jsonify({"success": True, "data": {"artisans": artisans}}), 200
