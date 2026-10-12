from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from backend.app.auth import auth_service
from backend.app.models.user import ArtisanProfile, PortfolioWork, User
from backend.app.services.storage import portfolio_image_url

bp = Blueprint("customers", __name__, url_prefix="/api/v1/customers")
service = auth_service
WORK_CATEGORIES = {"MAKEUP", "MEHENDI", "DRESS", "FULL_PACKAGE"}


@bp.get("/me")
def customer_profile():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401

    token = auth_header.split(" ", 1)[1].strip()
    claims = service.verify_token(token, "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401

    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403

    return jsonify({"success": True, "data": {"role": claims["role"], "email": claims["email"], "message": "Customer profile endpoint ready"}, "message": "Customer profile loaded"}), 200


@bp.get("/artisans")
def list_artisans():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403

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
