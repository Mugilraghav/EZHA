from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from sqlalchemy import select
from werkzeug.utils import secure_filename

from backend.app.auth import auth_service
from backend.app.models.user import ArtisanNotification, ArtisanProfile, Booking, PortfolioWork, User
from backend.app.services.commission import platform_commission_rate
from backend.app.services.payouts import mask_account_number, validate_bank_details
from backend.app.services.storage import StorageUploadError, SupabaseStorage, portfolio_image_url

bp = Blueprint("artisan", __name__, url_prefix="/api/v1/artisan")
service = auth_service
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
WORK_CATEGORIES = {"MAKEUP", "MEHENDI", "DRESS", "FULL_PACKAGE"}


def _portfolio_items(artisan_id):
    with current_app.extensions["ezha_session_factory"]() as session:
        works = session.scalars(
            select(PortfolioWork).where(PortfolioWork.artisan_id == artisan_id).order_by(PortfolioWork.created_at.desc())
        ).all()
        return [
            {
                "id": work.id,
                "artisan_id": work.artisan_id,
                "title": work.title,
                "category": work.category,
                "price": work.price,
                "caption": work.caption,
                "filename": work.filename,
                "storage_provider": work.storage_provider,
                "url": portfolio_image_url(work.filename, work.storage_provider),
            }
            for work in works
        ]


def _artisan_claims():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401)

    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return None, (jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401)
    if claims.get("role") != "ARTISAN":
        return None, (jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Artisan access required"}}), 403)
    return claims, None


@bp.get("/dashboard")
def dashboard():
    claims, error = _artisan_claims()
    if error:
        return error

    with current_app.extensions["ezha_session_factory"]() as session:
        booking_rows = session.execute(
            select(Booking, PortfolioWork, User)
            .join(PortfolioWork, PortfolioWork.id == Booking.work_id)
            .join(User, User.id == Booking.customer_id)
            .where(Booking.artisan_id == claims["sub"])
            .order_by(Booking.created_at.desc())
        ).all()
        profile = session.get(ArtisanProfile, claims["sub"])
        notifications = session.scalars(
            select(ArtisanNotification)
            .where(ArtisanNotification.artisan_id == claims["sub"])
            .order_by(ArtisanNotification.created_at.desc())
            .limit(20)
        ).all()
        bookings = [{
            "id": booking.id,
            "customer": customer.name,
            "service": work.title,
            "date": booking.service_date,
            "status": booking.status,
            "amount": booking.amount,
            "artisan_payout": booking.artisan_payout or booking.amount,
            "payment_status": booking.payment_status,
            "service_mode": booking.service_mode,
            "service_address": f"{booking.service_address_line1}, {booking.service_city} {booking.service_pincode}",
        } for booking, work, customer in booking_rows]
    demo_orders = ([
        {"id": "ord_2001", "customer": "Meera S.", "service": "Bridal Makeup Trial", "date": "2026-11-15", "status": "CONFIRMED", "amount": 8500},
        {"id": "ord_2002", "customer": "Rhea K.", "service": "Bridal Makeup Trial", "date": "2026-11-18", "status": "PENDING", "amount": 8500},
    ] if claims.get("username") == "ananya" and current_app.config.get("APP_ENV", "development") != "production" else [])
    orders = demo_orders + bookings
    total_earnings = sum(
        (order.get("artisan_payout") or order["amount"])
        for order in orders
        if order["status"] == "CONFIRMED" and order.get("payment_status") == "PAID"
    )
    portfolio = _portfolio_items(claims["sub"])
    payout_ready = bool(profile and profile.account_number and profile.ifsc_code)
    return jsonify({
        "success": True,
        "data": {
            "profile": {
                "name": claims["name"],
                "username": claims["username"],
                "city": profile.city if profile else "",
                "category": profile.category if profile else "",
            },
            "orders": orders,
            "payments": {
                "available_balance": total_earnings,
                "pending_balance": sum(order["amount"] for order in orders if order["status"] == "PENDING"),
                "currency": "INR",
                "commission_rate": platform_commission_rate(),
                "payout_account": {
                    "account_holder_name": profile.account_holder_name if profile else "",
                    "account_number_masked": mask_account_number(profile.account_number) if profile and profile.account_number else "",
                    "ifsc_code": profile.ifsc_code if profile else "",
                    "configured": payout_ready,
                },
            },
            "notifications": [{
                "id": note.id,
                "kind": note.kind,
                "title": note.title,
                "message": note.message,
                "booking_id": note.booking_id,
                "is_read": note.is_read,
                "created_at": note.created_at.isoformat(),
            } for note in notifications],
            "portfolio": portfolio,
            "metrics": {"total_orders": len(orders), "completed_orders": sum(order["status"] == "CONFIRMED" for order in orders)},
        },
    }), 200


@bp.get("/payout-profile")
def payout_profile():
    claims, error = _artisan_claims()
    if error:
        return error
    with current_app.extensions["ezha_session_factory"]() as session:
        profile = session.get(ArtisanProfile, claims["sub"])
    return jsonify({
        "success": True,
        "data": {
            "account_holder_name": profile.account_holder_name if profile else "",
            "account_number_masked": mask_account_number(profile.account_number) if profile and profile.account_number else "",
            "ifsc_code": profile.ifsc_code if profile else "",
            "configured": bool(profile and profile.account_number and profile.ifsc_code),
        },
    }), 200


@bp.patch("/payout-profile")
def update_payout_profile():
    claims, error = _artisan_claims()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    try:
        validate_bank_details(
            payload.get("account_holder_name", ""),
            payload.get("account_number", ""),
            payload.get("ifsc_code", ""),
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": {"code": "INVALID_BANK_DETAILS", "message": str(exc)}}), 400
    with current_app.extensions["ezha_session_factory"].begin() as session:
        profile = session.get(ArtisanProfile, claims["sub"])
        if profile is None:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Artisan profile not found"}}), 404
        profile.account_holder_name = str(payload.get("account_holder_name", "")).strip()[:160]
        profile.account_number = str(payload.get("account_number", "")).strip()[:32]
        profile.ifsc_code = str(payload.get("ifsc_code", "")).strip().upper()[:11]
    return jsonify({"success": True, "message": "Payout bank details saved. EZHA will transfer your 85% share after each paid booking."}), 200


@bp.post("/notifications/<notification_id>/read")
def mark_notification_read(notification_id):
    claims, error = _artisan_claims()
    if error:
        return error
    with current_app.extensions["ezha_session_factory"].begin() as session:
        note = session.scalar(
            select(ArtisanNotification).where(
                ArtisanNotification.id == notification_id,
                ArtisanNotification.artisan_id == claims["sub"],
            )
        )
        if not note:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Notification not found"}}), 404
        note.is_read = True
    return jsonify({"success": True}), 200


@bp.get("/portfolio")
def list_portfolio():
    claims, error = _artisan_claims()
    if error:
        return error
    items = _portfolio_items(claims["sub"])
    return jsonify({"success": True, "data": {"items": items}}), 200


@bp.post("/portfolio")
def upload_portfolio():
    claims, error = _artisan_claims()
    if error:
        return error
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"success": False, "error": {"code": "FILE_REQUIRED", "message": "Choose an image to upload"}}), 400

    safe_name = secure_filename(uploaded_file.filename)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"success": False, "error": {"code": "INVALID_FILE_TYPE", "message": "Upload a JPG, PNG, or WEBP image"}}), 400

    category = request.form.get("category", "MAKEUP").strip().upper()
    title = request.form.get("title", "").strip()[:160]
    caption = request.form.get("caption", "").strip()[:500]
    try:
        price = int(request.form.get("price", ""))
    except ValueError:
        return jsonify({"success": False, "error": {"code": "INVALID_PRICE", "message": "Enter a valid work price"}}), 400
    if category not in WORK_CATEGORIES:
        return jsonify({"success": False, "error": {"code": "INVALID_CATEGORY", "message": "Choose makeup, mehendi, dress, or full package"}}), 400
    if not title or price <= 0:
        return jsonify({"success": False, "error": {"code": "INVALID_WORK", "message": "A title and price greater than zero are required"}}), 400

    stored_name = f"{claims['sub']}_{uuid4().hex}.{extension}"
    storage = SupabaseStorage()
    if storage.partially_configured:
        return jsonify({"success": False, "error": {"code": "STORAGE_CONFIGURATION_INCOMPLETE", "message": "Complete all Supabase Storage settings"}}), 503
    if storage.configured:
        filename = f"portfolio/{stored_name}"
        try:
            image_url = storage.upload(uploaded_file.stream, filename, uploaded_file.mimetype)
        except StorageUploadError as exc:
            current_app.logger.warning("Portfolio image upload failed: %s", exc)
            return jsonify({"success": False, "error": {"code": "STORAGE_UPLOAD_FAILED", "message": str(exc)}}), 502
        storage_provider = "supabase"
    else:
        if current_app.config.get("APP_ENV") == "production":
            return jsonify({"success": False, "error": {"code": "STORAGE_NOT_CONFIGURED", "message": "Configure Supabase Storage before accepting portfolio uploads"}}), 503
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(upload_dir / stored_name)
        filename = stored_name
        storage_provider = "local"
        image_url = portfolio_image_url(filename, storage_provider)
    session_factory = current_app.extensions["ezha_session_factory"]
    with session_factory.begin() as session:
        work = PortfolioWork(
            artisan_id=claims["sub"],
            title=title,
            category=category,
            price=price,
            caption=caption,
            filename=filename,
            storage_provider=storage_provider,
        )
        session.add(work)
        session.flush()
        item = {
            "id": work.id,
            "artisan_id": work.artisan_id,
            "title": work.title,
            "category": work.category,
            "price": work.price,
            "caption": work.caption,
            "filename": work.filename,
            "storage_provider": work.storage_provider,
            "url": image_url,
        }
    return jsonify({"success": True, "data": item, "message": "Portfolio work uploaded"}), 201


@bp.get("/portfolio/<path:filename>")
def portfolio_image(filename):
    with current_app.extensions["ezha_session_factory"]() as session:
        work = session.scalar(select(PortfolioWork).where(PortfolioWork.filename == filename))
        storage_provider = work.storage_provider if work else None
    if not work:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Portfolio image not found"}}), 404
    if storage_provider == "supabase":
        from flask import redirect

        return redirect(SupabaseStorage().public_url(filename))
    return send_from_directory(Path(current_app.config["UPLOAD_FOLDER"]), filename)