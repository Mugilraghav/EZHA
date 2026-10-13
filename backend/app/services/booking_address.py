from __future__ import annotations


def service_mode_for_category(category: str) -> str:
    return "MAIL_IN" if category.upper() == "DRESS" else "DOORSTEP"


def validate_service_address(payload: dict, service_mode: str) -> dict:
    line1 = str(payload.get("address_line1", "")).strip()
    line2 = str(payload.get("address_line2", "")).strip()
    city = str(payload.get("address_city", payload.get("city", ""))).strip()
    state = str(payload.get("address_state", payload.get("state", ""))).strip()
    pincode = str(payload.get("pincode", "")).strip()
    if not line1 or not city or not state or not pincode:
        raise ValueError("Complete service address (street, city, state, and PIN code) is required")
    if not pincode.isdigit() or len(pincode) != 6:
        raise ValueError("Enter a valid 6-digit PIN code")
    return {
        "service_address_line1": line1[:200],
        "service_address_line2": line2[:200],
        "service_city": city[:100],
        "service_state": state[:100],
        "service_pincode": pincode[:10],
        "service_mode": service_mode,
    }
