from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.models.user import Booking
from backend.app.services.notifications import notify_artisan, notify_customer


def process_expired_acceptance_deadlines(session) -> int:
    now = datetime.now(timezone.utc)
    expired = session.scalars(
        select(Booking).where(
            Booking.payment_status == "PAID",
            Booking.artisan_decision == "PENDING",
            Booking.acceptance_deadline.is_not(None),
            Booking.acceptance_deadline < now,
        )
    ).all()
    count = 0
    for booking in expired:
        booking.artisan_decision = "AUTO_REJECTED"
        booking.status = "CANCELLED"
        booking.payment_status = "REFUNDED"
        booking.payout_status = "CANCELLED"
        notify_customer(
            session,
            booking.customer_id,
            "ORDER_REFUNDED",
            f"Order {booking.id[:8].upper()} refunded",
            f"The artisan did not confirm within 3 hours. ₹{booking.amount} will be returned to your payment method.",
            booking.id,
        )
        notify_artisan(
            session,
            booking.artisan_id,
            "ORDER_EXPIRED",
            "Order auto-cancelled",
            f"Order {booking.id[:8].upper()} was not confirmed in time and has been refunded to the customer.",
            booking.id,
        )
        count += 1
    return count
