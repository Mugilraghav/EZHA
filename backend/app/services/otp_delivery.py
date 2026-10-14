from __future__ import annotations

import smtplib
from email.message import EmailMessage

import requests
from flask import current_app


class OtpDeliveryError(RuntimeError):
    pass


def _smtp_configured() -> bool:
    return bool(current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_USERNAME"))


def _twilio_configured() -> bool:
    return bool(
        current_app.config.get("TWILIO_ACCOUNT_SID")
        and current_app.config.get("TWILIO_AUTH_TOKEN")
        and current_app.config.get("TWILIO_FROM_NUMBER")
    )


def send_email_otp(destination: str, code: str, purpose: str = "verify") -> None:
    if current_app.config.get("TESTING"):
        return
    if not _smtp_configured():
        if current_app.config.get("APP_ENV") == "production":
            raise OtpDeliveryError(
                "Email OTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD on the server."
            )
        return
    subject = "Your EZHA verification code"
    if purpose == "reset":
        subject = "Your EZHA password reset code"
    body = (
        f"Your EZHA verification code is {code}.\n\n"
        "It expires in 15 minutes. If you did not request this, you can ignore this email."
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config.get("SMTP_FROM") or current_app.config["SMTP_USERNAME"]
    message["To"] = destination
    message.set_content(body)
    port = int(current_app.config.get("SMTP_PORT", 587))
    use_tls = current_app.config.get("SMTP_USE_TLS", "true").lower() == "true"
    with smtplib.SMTP(current_app.config["SMTP_HOST"], port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        password = current_app.config.get("SMTP_PASSWORD", "")
        if password:
            smtp.login(current_app.config["SMTP_USERNAME"], password)
        smtp.send_message(message)


def send_sms_otp(phone_e164: str, code: str) -> None:
    if current_app.config.get("TESTING"):
        return
    if not _twilio_configured():
        if current_app.config.get("APP_ENV") == "production":
            raise OtpDeliveryError(
                "SMS OTP is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER."
            )
        return
    to_number = phone_e164 if phone_e164.startswith("+") else f"+{phone_e164}"
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{current_app.config['TWILIO_ACCOUNT_SID']}/Messages.json"
    )
    response = requests.post(
        url,
        auth=(current_app.config["TWILIO_ACCOUNT_SID"], current_app.config["TWILIO_AUTH_TOKEN"]),
        data={
            "From": current_app.config["TWILIO_FROM_NUMBER"],
            "To": to_number,
            "Body": f"Your EZHA verification code is {code}. Valid for 15 minutes.",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise OtpDeliveryError("SMS provider could not deliver the verification code. Try again shortly.")


def deliver_otp(channel: str, destination: str, code: str, purpose: str = "verify") -> None:
    if channel == "email":
        send_email_otp(destination, code, purpose)
    else:
        send_sms_otp(destination, code)
