from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.app.auth import auth_service

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


@bp.get("/demo")
def demo_login():
    if current_app.config.get("APP_ENV") == "production":
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Not found"}}), 404
    return jsonify({"success": True, "data": {"customer": {"username": "customer", "password": "demo123"}, "artisan": {"username": "ananya", "password": "demo123"}, "admin": {"username": "admin", "password": "demo123"}}, "message": "Demo credentials available in development"})
