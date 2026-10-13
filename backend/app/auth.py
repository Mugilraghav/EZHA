from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.app.models.user import ArtisanProfile, CustomerProfile, OtpChallenge, User


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        return f"91{digits}"
    return digits


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
            "phone": user.phone,
            "username": user.username,
            "role": user.role,
            "name": user.name,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
        }

    def _generate_username(self, session, base: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "", base.lower())[:24] or "ezha"
        candidate = slug
        suffix = 0
        while session.scalar(select(User.id).where(User.username == candidate)):
            suffix += 1
            candidate = f"{slug}{suffix}"
        return candidate

    def send_otp(self, channel: str, destination: str, purpose: str = "verify") -> Dict[str, Any]:
        channel = channel.lower().strip()
        if channel not in {"email", "phone"}:
            raise ValueError("Choose email or phone for verification")
        dest = destination.lower().strip() if channel == "email" else normalize_phone(destination)
        if channel == "email" and "@" not in dest:
            raise ValueError("Enter a valid email address")
        if channel == "phone" and len(dest) < 10:
            raise ValueError("Enter a valid mobile number")
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        session_factory = self._session_factory()
        with session_factory.begin() as session:
            session.add(
                OtpChallenge(
                    channel=channel,
                    destination=dest,
                    code_hash=generate_password_hash(code),
                    purpose=purpose,
                    expires_at=expires_at,
                )
            )
        payload: Dict[str, Any] = {"channel": channel, "destination": dest, "expires_in_seconds": 900}
        if current_app.config.get("APP_ENV") != "production":
            payload["dev_code"] = code
        return payload

    def verify_otp(self, channel: str, destination: str, code: str, purpose: str = "verify") -> bool:
        channel = channel.lower().strip()
        dest = destination.lower().strip() if channel == "email" else normalize_phone(destination)
        now = datetime.now(timezone.utc)
        with self._session_factory()() as session:
            challenges = session.scalars(
                select(OtpChallenge)
                .where(
                    OtpChallenge.channel == channel,
                    OtpChallenge.destination == dest,
                    OtpChallenge.purpose == purpose,
                )
                .order_by(OtpChallenge.created_at.desc())
                .limit(5)
            ).all()
            for challenge in challenges:
                if challenge.expires_at < now:
                    continue
                if check_password_hash(challenge.code_hash, code.strip()):
                    session.delete(challenge)
                    session.commit()
                    return True
        return False

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
        email_otp: str = "",
        phone_otp: str = "",
    ) -> Dict[str, Any]:
        email_key = email.lower().strip()
        role = "ARTISAN" if role.upper() == "VENDOR" else role.upper()
        if not password:
            raise ValueError("Password is required")
        if role not in {"CUSTOMER", "ARTISAN"}:
            raise ValueError("Registration is available for customers and artisans only")
        category = category.strip().upper() or "MAKEUP"
        if role == "ARTISAN" and category not in {"MAKEUP", "MEHENDI", "DRESS", "FULL_PACKAGE"}:
            raise ValueError("Choose makeup, mehendi, dress, or full package as your category")
        if not email_key:
            raise ValueError("Email is required")
        phone_key = normalize_phone(phone)
        if not phone_key:
            raise ValueError("Mobile number is required")
        testing = bool(current_app.config.get("TESTING"))
        if testing:
            verified_email = verified_phone = True
        else:
            if not email_otp or not phone_otp:
                raise ValueError("Verify your email and mobile with the codes we sent")
            verified_email = self.verify_otp("email", email_key, email_otp)
            verified_phone = self.verify_otp("phone", phone_key, phone_otp)
            if not verified_email:
                raise ValueError("Email verification code is invalid or expired")
            if not verified_phone:
                raise ValueError("Mobile verification code is invalid or expired")
        session_factory = self._session_factory()
        try:
            with session_factory.begin() as session:
                username_key = username.lower().strip()
                if not username_key:
                    username_key = self._generate_username(session, name or email_key.split("@", 1)[0])
                identity_filters = [User.email == email_key, User.username == username_key]
                if phone_key:
                    identity_filters.append(User.phone == phone_key)
                existing = session.scalar(select(User.id).where(or_(*identity_filters)))
                if existing:
                    raise ValueError("Username, email, or mobile already exists")
                user = User(
                    username=username_key,
                    email=email_key,
                    phone=phone_key,
                    name=name.strip() or username_key,
                    password_hash=generate_password_hash(password),
                    role=role,
                    email_verified=verified_email,
                    phone_verified=verified_phone,
                )
                session.add(user)
                session.flush()
                if role == "ARTISAN":
                    session.add(
                        ArtisanProfile(
                            artisan_id=user.id,
                            city=city.strip()[:100],
                            category=category,
                            account_holder_name="",
                            account_number="",
                            ifsc_code="",
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
        phone_key = normalize_phone(identifier)
        with self._session_factory()() as session:
            filters = [User.username == identifier_key, User.email == identifier_key]
            if phone_key:
                filters.append(User.phone == phone_key)
            user = session.scalar(select(User).where(or_(*filters)))
            if not user or not check_password_hash(user.password_hash, password):
                return None
            return self._serialize_user(user)

    def reset_password(self, identifier: str, otp: str, new_password: str) -> None:
        if len(new_password or "") < 8:
            raise ValueError("Choose a password with at least 8 characters")
        identifier_key = identifier.lower().strip()
        phone_key = normalize_phone(identifier)
        channel = "email" if "@" in identifier_key else "phone"
        destination = identifier_key if channel == "email" else phone_key
        if not self.verify_otp(channel, destination, otp, purpose="reset"):
            raise ValueError("Reset code is invalid or expired")
        with self._session_factory.begin() as session:
            filters = [User.username == identifier_key, User.email == identifier_key]
            if phone_key:
                filters.append(User.phone == phone_key)
            user = session.scalar(select(User).where(or_(*filters)))
            if not user:
                raise ValueError("No account found for this email or mobile number")
            user.password_hash = generate_password_hash(new_password)

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
