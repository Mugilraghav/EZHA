from __future__ import annotations

from flask import current_app


def platform_commission_rate() -> float:
    return float(current_app.config.get("PLATFORM_COMMISSION_RATE", 0.15))


def split_gross_amount(gross_amount: int) -> tuple[int, int]:
    """Return (platform_fee, artisan_payout) in whole rupees."""
    rate = platform_commission_rate()
    platform_fee = int(round(gross_amount * rate))
    artisan_payout = gross_amount - platform_fee
    return platform_fee, artisan_payout
