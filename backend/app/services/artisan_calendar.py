from __future__ import annotations

from sqlalchemy import select

from backend.app.models.user import ArtisanCalendarBlock, Booking


ACTIVE_BOOKING_STATUSES = {"AWAITING_ARTISAN", "CONFIRMED", "PENDING"}


def artisan_month_availability(session, artisan_id: str, year: int, month: int) -> dict:
    prefix = f"{year:04d}-{month:02d}-"
    blocks = session.scalars(
        select(ArtisanCalendarBlock).where(
            ArtisanCalendarBlock.artisan_id == artisan_id,
            ArtisanCalendarBlock.block_date.startswith(prefix),
        )
    ).all()
    bookings = session.scalars(
        select(Booking).where(
            Booking.artisan_id == artisan_id,
            Booking.service_date.startswith(prefix),
            Booking.status.in_(tuple(ACTIVE_BOOKING_STATUSES)),
            Booking.payment_status.in_(("PAID", "PAYMENT_PENDING", "UNPAID")),
        )
    ).all()
    blocked_dates = {block.block_date for block in blocks if not block.start_time}
    busy_slots = {}
    for booking in bookings:
        if booking.payment_status == "REFUNDED":
            continue
        busy_slots.setdefault(booking.service_date, []).append(booking.service_time)
    days = {}
    for day in range(1, 32):
        date_key = f"{year:04d}-{month:02d}-{day:02d}"
        if not date_key.startswith(prefix):
            continue
        try:
            from datetime import date

            date(year, month, day)
        except ValueError:
            continue
        if date_key in blocked_dates:
            days[date_key] = {"status": "blocked", "slots": []}
        elif date_key in busy_slots:
            days[date_key] = {"status": "partial", "slots": sorted(busy_slots[date_key])}
        else:
            days[date_key] = {"status": "available", "slots": []}
    return {"year": year, "month": month, "days": days, "blocks": [
        {
            "date": block.block_date,
            "start_time": block.start_time,
            "end_time": block.end_time,
            "reason": block.reason,
        }
        for block in blocks
    ]}


def slot_is_available(session, artisan_id: str, service_date: str, service_time: str) -> bool:
    block = session.scalar(
        select(ArtisanCalendarBlock).where(
            ArtisanCalendarBlock.artisan_id == artisan_id,
            ArtisanCalendarBlock.block_date == service_date,
        )
    )
    if block and (not block.start_time or block.start_time == service_time):
        return False
    conflict = session.scalar(
        select(Booking.id).where(
            Booking.artisan_id == artisan_id,
            Booking.service_date == service_date,
            Booking.service_time == service_time,
            Booking.status.in_(tuple(ACTIVE_BOOKING_STATUSES)),
            Booking.payment_status == "PAID",
            Booking.artisan_decision.in_(("PENDING", "ACCEPTED")),
        )
    )
    return conflict is None
