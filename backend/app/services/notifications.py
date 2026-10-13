from __future__ import annotations

from backend.app.models.user import ArtisanNotification


def notify_artisan(session, artisan_id: str, kind: str, title: str, message: str, booking_id: str | None = None) -> None:
    session.add(
        ArtisanNotification(
            artisan_id=artisan_id,
            booking_id=booking_id,
            kind=kind,
            title=title,
            message=message,
        )
    )
