from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.app.models.user import ArtisanProfile, CustomerProfile, User
from backend.app.services.payouts import validate_bank_details


class SimpleAuthService:
    """Database-backed account operations and signed token helpers."""

    @staticmethod
    def _session_factory():
        return current_app.extensions["ezha_session_factory"]

    @staticmethod
    def _serialize_user(user: User) -> Dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "name": user.name,
        }

    @staticmethod
    def _encode_base64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _decode_base64(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + padding).encode("utf-8"))

    def _secret(self) -> str:
        return current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY") or "dev-secret-key"

    def register(
        self,
        email: str,
        password: str,
        role: str = "CUSTOMER",
        name: str = "",
        username: str = "",
        city: str = "",
        category: str = "MAKEUP",
        account_holder_name: str = "",
        account_number: str = "",
        ifsc_code: str = "",
        phone: str = "",
        address_line1: str = "",
        address_line2: str = "",
        address_city: str = "",
        address_state: str = "",
        pincode: str = "",
    ) -> Dict[str, Any]:
        email_key = email.lower().strip()
        username_key = username.lower().strip() or email_key.split("@", 1)[0]
        role = "ARTISAN" if role.upper() == "VENDOR" else role.upper()
        if not username_key or not password:
            raise ValueError("Username and password are required")
        if role not in {"CUSTOMER", "ARTISAN"}:
            raise ValueError("Registration is available for customers and artisans only")
        category = category.strip().upper() or "MAKEUP"
        if role == "ARTISAN" and category not in {"MAKEUP", "MEHENDI", "DRESS", "FULL_PACKAGE"}:
            raise ValueError("Choose makeup, mehendi, dress, or full package as your category")
        if role == "ARTISAN":
            validate_bank_details(account_holder_name, account_number, ifsc_code)
        if not email_key:
            raise ValueError("Email is required")
        session_factory = self._session_factory()
        try:
            with session_factory.begin() as session:
                existing = session.scalar(select(User.id).where(or_(User.username == username_key, User.email == email_key)))
                if existing:
                    raise ValueError("Username or email already exists")
                user = User(
                    username=username_key,
                    email=email_key,
                    name=name.strip() or username_key,
                    password_hash=generate_password_hash(password),
                    role=role,
                )
                session.add(user)
                session.flush()
                if role == "ARTISAN":
                    session.add(
                        ArtisanProfile(
                            artisan_id=user.id,
                            city=city.strip()[:100],
                            category=category,
                            account_holder_name=account_holder_name.strip()[:160],
                            account_number=account_number.strip()[:32],
                            ifsc_code=ifsc_code.strip().upper()[:11],
                        )
                    )
                if role == "CUSTOMER" and any([phone, address_line1, address_city, pincode]):
                    session.add(
                        CustomerProfile(
                            customer_id=user.id,
                            phone=phone.strip()[:20],
                            address_line1=address_line1.strip()[:200],
                            address_line2=address_line2.strip()[:200],
                            city=address_city.strip()[:100],
                            state=address_state.strip()[:100],
                            pincode=pincode.strip()[:10],
                        )
                    )
                result = self._serialize_user(user)
        except IntegrityError as exc:
            raise ValueError("Username or email already exists") from exc
        return result

    def authenticate(self, identifier: str, password: str) -> Optional[Dict[str, Any]]:
        identifier_key = identifier.lower().strip()
        with self._session_factory()() as session:
            user = session.scalar(select(User).where(or_(User.username == identifier_key, User.email == identifier_key)))
            if not user or not check_password_hash(user.password_hash, password):
                return None
            return self._serialize_user(user)

    def user_counts(self) -> Dict[str, int]:
        with self._session_factory()() as session:
            rows = session.execute(select(User.role, func.count(User.id)).group_by(User.role)).all()
        return {role: count for role, count in rows}

    def issue_token(self, user: Dict[str, Any], token_type: str = "access") -> str:
        secret = self._secret()
        expires_delta = timedelta(hours=1 if token_type == "access" else 24)
        expires_at = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "username": user["username"],
            "role": user["role"],
            "name": user["name"],
            "token_type": token_type,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        header_segment = self._encode_base64(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_segment = self._encode_base64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        return f"{header_segment}.{payload_segment}.{self._encode_base64(signature)}"

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        try:
            header_segment, payload_segment, signature = token.split(".")
            expected_signature = self._encode_base64(
                hmac.new(self._secret().encode("utf-8"), f"{header_segment}.{payload_segment}".encode("utf-8"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(signature, expected_signature):
                return None
            payload = json.loads(self._decode_base64(payload_segment).decode("utf-8"))
            if payload.get("token_type") != token_type:
                return None
            if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
                return None
            return payload
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def require_role(self, user: Dict[str, Any], allowed_roles: set[str]) -> bool:
        return user.get("role") in allowed_roles


auth_service = SimpleAuthService()
