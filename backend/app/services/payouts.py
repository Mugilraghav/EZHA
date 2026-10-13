from __future__ import annotations

import re

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def normalize_ifsc(value: str) -> str:
    return value.strip().upper()


def validate_bank_details(account_holder: str, account_number: str, ifsc_code: str) -> None:
    holder = account_holder.strip()
    account = account_number.strip()
    ifsc = normalize_ifsc(ifsc_code)
    if len(holder) < 2:
        raise ValueError("Account holder name is required")
    if not account.isdigit() or not (9 <= len(account) <= 18):
        raise ValueError("Enter a valid bank account number (9–18 digits)")
    if not IFSC_PATTERN.match(ifsc):
        raise ValueError("Enter a valid IFSC code (for example, HDFC0001234)")
    return None


def mask_account_number(account_number: str) -> str:
    digits = account_number.strip()
    if len(digits) <= 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"
