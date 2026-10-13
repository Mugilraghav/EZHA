from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func, select

from backend.app.models.user import Booking, User
from backend.app.services.storage import SupabaseStorage

bp = Blueprint("public_api", __name__, url_prefix="/api/v1/public")


def _public_image_url(path_key: str, fallback: str) -> str:
    object_path = (current_app.config.get(path_key) or "").strip()
    if not object_path:
        return fallback
    storage = SupabaseStorage()
    if storage.configured:
        try:
            return storage.public_url(object_path)
        except Exception:
            return fallback
    return fallback


@bp.get("/stats")
def platform_stats():
    session_factory = current_app.extensions["ezha_session_factory"]
    with session_factory() as session:
        bookings_completed = session.scalar(
            select(func.count(Booking.id)).where(Booking.status.in_(("CONFIRMED", "COMPLETED", "PAID")))
        ) or 0
        if bookings_completed == 0:
            bookings_completed = session.scalar(select(func.count(Booking.id))) or 0
        verified_artists = session.scalar(
            select(func.count(User.id)).where(User.role == "ARTISAN")
        ) or 0
    return jsonify(
        {
            "success": True,
            "data": {
                "bookings_completed": int(bookings_completed),
                "verified_artists": int(verified_artists),
                "customer_rating": "4.9/5",
                "support_access": "24/7",
            },
        }
    )


@bp.get("/site-config")
def site_config():
    hero_fallback = "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80"
    founder_fallback = hero_fallback
    return jsonify(
        {
            "success": True,
            "data": {
                "hero_image_url": _public_image_url("LANDING_HERO_PATH", hero_fallback),
                "founder_image_url": _public_image_url("FOUNDER_IMAGE_PATH", founder_fallback),
                "founder_name": current_app.config.get("FOUNDER_NAME", "Mugilraghav"),
                "support_email": current_app.config.get("SUPPORT_EMAIL", "vimala8121983@gmail.com"),
            },
        }
    )
