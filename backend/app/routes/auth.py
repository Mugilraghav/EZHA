from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from sqlalchemy import or_, select

from backend.app.auth import auth_service, normalize_phone
from backend.app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
service = auth_service


@bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "")
    username = payload.get("username", "")
    password = payload.get("password", "")
    name = payload.get("name", "")
    role = payload.get("role", "CUSTOMER")
    city = payload.get("city", "")
    category = payload.get("category", "MAKEUP")

    try:
        user = service.register(
            email=email,
            password=password,
            role=role,
            name=name,
            username=username,
            city=city,
            category=category,
            account_holder_name=payload.get("account_holder_name", ""),
            account_number=payload.get("account_number", ""),
            ifsc_code=payload.get("ifsc_code", ""),
            phone=payload.get("phone", ""),
            email_otp=payload.get("email_otp", ""),
            phone_otp=payload.get("phone_otp", ""),
            address_line1=payload.get("address_line1", ""),
            address_line2=payload.get("address_line2", ""),
            address_city=payload.get("address_city", ""),
            address_state=payload.get("address_state", ""),
            pincode=payload.get("pincode", ""),
        )
        return jsonify({"success": True, "data": user, "message": "Registration successful"}), 201
    except ValueError as exc:
        return jsonify({"success": False, "error": {"code": "REGISTRATION_FAILED", "message": str(exc)}}), 400


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    user = service.authenticate(
        payload.get("username") or payload.get("identifier") or payload.get("email", ""),
        payload.get("password", ""),
    )
    if not user:
        return jsonify({"success": False, "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}}), 401
    requested_role = payload.get("role")
    if requested_role:
        requested_role = "ARTISAN" if requested_role.upper() == "VENDOR" else requested_role.upper()
        if requested_role not in {"CUSTOMER", "ARTISAN", "ADMIN"}:
            return jsonify({"success": False, "error": {"code": "INVALID_ROLE", "message": "Choose a valid login type"}}), 400
        if user["role"] != requested_role:
            return jsonify({"success": False, "error": {"code": "ROLE_MISMATCH", "message": "These credentials do not belong to this login type"}}), 403
    tokens = {
        "access_token": service.issue_token(user, "access"),
        "refresh_token": service.issue_token(user, "refresh"),
        "user": user,
    }
    return jsonify({"success": True, "data": tokens, "message": "Login successful"}), 200


@bp.post("/refresh")
def refresh():
    payload = request.get_json(silent=True) or {}
    token = payload.get("refresh_token") or payload.get("token")
    if not token:
        return jsonify({"success": False, "error": {"code": "MISSING_TOKEN", "message": "Refresh token is required"}}), 401
    claims = service.verify_token(token, "refresh")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Refresh token is invalid or expired"}}), 401
    user = {"id": claims["sub"], "email": claims["email"], "role": claims["role"], "name": claims["name"]}
    return jsonify({"success": True, "data": {"access_token": service.issue_token(user, "access")}, "message": "Token refresh successful"}), 200


@bp.post("/otp/send")
def send_otp():
    payload = request.get_json(silent=True) or {}
    try:
        data = service.send_otp(
            payload.get("channel", ""),
            payload.get("destination", ""),
            purpose=payload.get("purpose", "verify"),
        )
        return jsonify({"success": True, "data": data, "message": "Verification code sent"}), 200
    except ValueError as exc:
        return jsonify({"success": False, "error": {"code": "OTP_FAILED", "message": str(exc)}}), 400


@bp.post("/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    identifier = (payload.get("identifier") or payload.get("email") or payload.get("phone") or "").strip()
    if not identifier:
        return jsonify({"success": False, "error": {"code": "MISSING_IDENTIFIER", "message": "Enter your email or mobile number"}}), 400
    identifier_key = identifier.lower()
    phone_key = normalize_phone(identifier)
    session_factory = current_app.extensions["ezha_session_factory"]
    with session_factory() as session:
        filters = [User.email == identifier_key, User.username == identifier_key]
        if phone_key:
            filters.append(User.phone == phone_key)
        user = session.scalar(select(User).where(or_(*filters)))
    if not user:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "No account found for this email or mobile number"}}), 404
    channel = "email" if "@" in identifier_key else "phone"
    destination = user.email if channel == "email" else user.phone
    try:
        data = service.send_otp(channel, destination, purpose="reset")
        return jsonify({"success": True, "data": data, "message": "Password reset code sent"}), 200
    except ValueError as exc:
        return jsonify({"success": False, "error": {"code": "OTP_FAILED", "message": str(exc)}}), 400


@bp.post("/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    try:
        service.reset_password(
            payload.get("identifier", ""),
            payload.get("otp", "") or payload.get("code", ""),
            payload.get("new_password", "") or payload.get("password", ""),
        )
        return jsonify({"success": True, "message": "Password updated. You can sign in now."}), 200
    except ValueError as exc:
        return jsonify({"success": False, "error": {"code": "RESET_FAILED", "message": str(exc)}}), 400


@bp.get("/demo")
def demo_login():
    if current_app.config.get("APP_ENV") == "production":
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Not found"}}), 404
    return jsonify({"success": True, "data": {"customer": {"username": "customer", "password": "demo123"}, "artisan": {"username": "ananya", "password": "demo123"}, "admin": {"username": "admin", "password": "demo123"}}, "message": "Demo credentials available in development"})
