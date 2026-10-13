from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import select

from backend.app.models.user import ArtisanProfile, PortfolioWork, User
from backend.app.services.storage import portfolio_image_url


def artisan_payout_ready(profile: ArtisanProfile | None) -> bool:
    if not profile:
        return False
    return bool(profile.account_holder_name and profile.account_number and profile.ifsc_code)


def listing_visible_at(created_at: datetime) -> datetime:
    buffer_minutes = int(current_app.config.get("PORTFOLIO_LISTING_BUFFER_MINUTES", 15))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(minutes=buffer_minutes)


def query_customer_works(session, category: str = "", city: str = "", search: str = ""):
    now = datetime.now(timezone.utc)
    rows = session.execute(
        select(PortfolioWork, User, ArtisanProfile)
        .join(User, User.id == PortfolioWork.artisan_id)
        .join(ArtisanProfile, ArtisanProfile.artisan_id == User.id)
        .where(User.role == "ARTISAN")
        .order_by(PortfolioWork.created_at.desc())
    ).all()
    works = []
    city_key = city.casefold()
    search_key = search.casefold()
    for work, artisan, profile in rows:
        if not artisan_payout_ready(profile):
            continue
        visible_at = listing_visible_at(work.created_at)
        if visible_at > now:
            continue
        if category and work.category != category:
            continue
        if city_key and profile.city.casefold() != city_key:
            continue
        blob = f"{work.title} {work.caption} {artisan.name} {profile.city}".casefold()
        if search_key and search_key not in blob:
            continue
        works.append({
            "id": work.id,
            "title": work.title,
            "category": work.category,
            "price": work.price,
            "caption": work.caption,
            "image_url": portfolio_image_url(work.filename, work.storage_provider),
            "artisan_id": artisan.id,
            "artisan_name": artisan.name,
            "artisan_username": artisan.username,
            "artisan_city": profile.city,
            "listed_at": visible_at.isoformat(),
        })
    return works
