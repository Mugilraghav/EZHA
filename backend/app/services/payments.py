from flask import current_app


class PaymentConfigurationError(RuntimeError):
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

    def _client(self):
        key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
        key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
        if not key_id or not key_secret:
            raise PaymentConfigurationError("Razorpay keys are not configured")
        import razorpay

        return key_id, razorpay.Client(auth=(key_id, key_secret))

    def create_payment(self, amount, currency="INR", **kwargs):
        key_id, client = self._client()
        order = client.order.create(data={
            "amount": int(amount) * 100,
            "currency": currency,
            "receipt": str(kwargs.get("receipt", "ezha-booking"))[:40],
        })
        return {
            "provider": self.provider_name,
            "key_id": key_id,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": currency,
            "status": order["status"],
        }

    def verify_payment(self, payload, **kwargs):
        _, client = self._client()
        client.utility.verify_payment_signature(payload)
        return {"provider": self.provider_name, "status": "verified"}
