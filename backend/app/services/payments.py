import hashlib
import hmac

import requests
from flask import current_app


class PaymentConfigurationError(RuntimeError):
    pass


class PaymentAuthenticationError(RuntimeError):
    pass


class PaymentProviderError(RuntimeError):
    pass


class PaymentSignatureError(ValueError):
    pass


class PaymentProvider:
    """Base abstraction for payment providers."""

    provider_name = "base"

    def create_payment(self, amount, currency="INR", **kwargs):
        raise NotImplementedError("Payment provider must implement create_payment()")

    def verify_payment(self, payload, **kwargs):
        raise NotImplementedError("Payment provider must implement verify_payment()")


class RazorpayProvider(PaymentProvider):
    """Razorpay order creation and signature verification."""

    provider_name = "razorpay"

    def _credentials(self):
        key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
        key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
        if not key_id or not key_secret:
            raise PaymentConfigurationError("Razorpay keys are not configured")
        return key_id, key_secret

    def create_payment(self, amount, currency="INR", **kwargs):
        key_id, key_secret = self._credentials()
        order_data = {
            "amount": int(amount) * 100,
            "currency": currency,
            "receipt": str(kwargs.get("receipt", "ezha-booking"))[:40],
        }
        try:
            response = requests.post(
                "https://api.razorpay.com/v1/orders",
                auth=(key_id, key_secret),
                json=order_data,
                timeout=20,
            )
            if response.status_code == 401:
                raise PaymentAuthenticationError("Razorpay rejected the configured key pair")
            response.raise_for_status()
            order = response.json()
        except PaymentAuthenticationError:
            raise
        except requests.RequestException as exc:
            raise PaymentProviderError("Razorpay could not create the order") from exc
        except (ValueError, KeyError) as exc:
            raise PaymentProviderError("Razorpay returned an invalid order response") from exc
        return {
            "provider": self.provider_name,
            "key_id": key_id,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": currency,
            "status": order["status"],
        }

    def verify_payment(self, payload, **kwargs):
        _, key_secret = self._credentials()
        order_id = payload.get("razorpay_order_id", "")
        payment_id = payload.get("razorpay_payment_id", "")
        signature = payload.get("razorpay_signature", "")
        if not order_id or not payment_id or not signature:
            raise PaymentSignatureError("Razorpay payment fields are required")
        expected_signature = hmac.new(
            key_secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise PaymentSignatureError("Razorpay payment signature is invalid")
        return {"provider": self.provider_name, "status": "verified"}
