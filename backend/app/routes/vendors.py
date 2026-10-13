from flask import Blueprint, current_app, jsonify, request

from backend.app.auth import auth_service
from backend.app.models.catalog import get_demo_catalog
from backend.app.models.user import ArtisanProfile, Booking, PortfolioWork, User
from backend.app.services.payments import (
    PaymentAuthenticationError,
    PaymentConfigurationError,
    PaymentProviderError,
    PaymentSignatureError,
    RazorpayProvider,
)
from backend.app.services.booking_address import service_mode_for_category, validate_service_address
from backend.app.services.commission import platform_commission_rate, split_gross_amount
from backend.app.services.notifications import notify_artisan
from backend.app.services.storage import portfolio_image_url
from sqlalchemy import select

bp = Blueprint("vendors", __name__, url_prefix="/api/v1")
service = auth_service


@bp.get("/vendors")
def list_vendors():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401

    token = auth_header.split(" ", 1)[1].strip()
    claims = service.verify_token(token, "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401

    catalog = get_demo_catalog()
    return jsonify({"success": True, "data": {"vendors": catalog["vendors"], "message": "Vendor list endpoint ready"}, "message": "Vendors loaded"}), 200


@bp.get("/services")
def list_services():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401

    token = auth_header.split(" ", 1)[1].strip()
    claims = service.verify_token(token, "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401

    catalog = get_demo_catalog()
    return jsonify({"success": True, "data": {"services": catalog["services"], "message": "Service catalog ready"}, "message": "Services loaded"}), 200


@bp.get("/vendors/<vendor_id>")
def vendor_detail(vendor_id):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    catalog = get_demo_catalog()
    vendor = next((item for item in catalog["vendors"] if item["id"] == vendor_id), None)
    if not vendor:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Vendor not found"}}), 404
    services = [item for item in catalog["services"] if item["vendor_id"] == vendor_id]
    return jsonify({"success": True, "data": {"vendor": vendor, "services": services}}), 200


@bp.get("/services/<service_id>")
def service_detail(service_id):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    catalog = get_demo_catalog()
    item = next((item for item in catalog["services"] if item["id"] == service_id), None)
    if not item:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Service not found"}}), 404
    return jsonify({"success": True, "data": {"service": item}}), 200


@bp.post("/bookings")
def create_booking():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer account required to book"}}), 403

    payload = request.get_json(silent=True) or {}
    work_id = payload.get("work_id")
    if work_id:
        if not payload.get("date") or not payload.get("time"):
            return jsonify({"success": False, "error": {"code": "MISSING_SCHEDULE", "message": "Booking date and time are required"}}), 400
        session_factory = current_app.extensions["ezha_session_factory"]
        with session_factory.begin() as session:
            result = session.execute(
                select(PortfolioWork, User, ArtisanProfile)
                .join(User, User.id == PortfolioWork.artisan_id)
                .join(ArtisanProfile, ArtisanProfile.artisan_id == User.id)
                .where(PortfolioWork.id == work_id, User.role == "ARTISAN")
            ).first()
            if not result:
                return jsonify({"success": False, "error": {"code": "WORK_NOT_FOUND", "message": "This artisan work is no longer available"}}), 404
            work, artisan, profile = result
            try:
                address_fields = validate_service_address(payload, service_mode_for_category(work.category))
            except ValueError as exc:
                return jsonify({"success": False, "error": {"code": "INVALID_ADDRESS", "message": str(exc)}}), 400
            if not profile.account_number or not profile.ifsc_code:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "ARTISAN_PAYOUT_INCOMPLETE",
                        "message": "This artisan has not added bank details yet. Choose another artisan or try again later.",
                    },
                }), 409
            booking = Booking(
                customer_id=claims["sub"],
                artisan_id=artisan.id,
                work_id=work.id,
                service_date=str(payload["date"]),
                service_time=str(payload["time"]),
                notes=str(payload.get("notes", ""))[:1000],
                amount=work.price,
                **address_fields,
            )
            session.add(booking)
            session.flush()
            mode_label = "mail-in tailoring" if booking.service_mode == "MAIL_IN" else "doorstep service"
            notify_artisan(
                session,
                artisan.id,
                "NEW_ORDER",
                "New booking request",
                f"{claims.get('name', 'A customer')} requested {work.title} ({mode_label}) on {booking.service_date}.",
                booking.id,
            )
            platform_fee, artisan_payout = split_gross_amount(work.price)
            booking_data = {
                "id": booking.id,
                "work_id": work.id,
                "work_title": work.title,
                "category": work.category,
                "customer_id": claims["sub"],
                "artisan_id": artisan.id,
                "artisan_name": artisan.name,
                "artisan_username": artisan.username,
                "artisan_city": profile.city,
                "date": booking.service_date,
                "time": booking.service_time,
                "notes": booking.notes,
                "amount": booking.amount,
                "platform_fee": platform_fee,
                "artisan_payout": artisan_payout,
                "commission_rate": platform_commission_rate(),
                "service_mode": booking.service_mode,
                "service_address": {
                    "line1": booking.service_address_line1,
                    "line2": booking.service_address_line2,
                    "city": booking.service_city,
                    "state": booking.service_state,
                    "pincode": booking.service_pincode,
                },
                "status": booking.status,
                "payment_status": booking.payment_status,
            }
        return jsonify({"success": True, "data": booking_data, "message": "Booking request created. Continue to checkout."}), 201

    catalog = get_demo_catalog()
    selected_service = next((item for item in catalog["services"] if item["id"] == payload.get("service_id")), None)
    if not selected_service or selected_service["vendor_id"] != payload.get("vendor_id"):
        return jsonify({"success": False, "error": {"code": "INVALID_SERVICE", "message": "Choose a valid service and vendor"}}), 400
    if not payload.get("date") or not payload.get("time"):
        return jsonify({"success": False, "error": {"code": "MISSING_SCHEDULE", "message": "Booking date and time are required"}}), 400

    booking = {
        "id": f"ord_{len(current_app.extensions['ezha_bookings']) + 3001}",
        "customer_id": claims["sub"],
        "customer": claims["name"],
        "vendor_id": selected_service["vendor_id"],
        "service_id": selected_service["id"],
        "service": selected_service["title"],
        "date": payload["date"],
        "time": payload["time"],
        "notes": str(payload.get("notes", ""))[:1000],
        "guest_count": max(1, min(int(payload.get("guest_count", 1)), 50)),
        "amount": selected_service["price"],
        "status": "PENDING",
    }
    current_app.extensions["ezha_bookings"].append(booking)
    return jsonify({"success": True, "data": booking, "message": "Booking request created"}), 201


@bp.get("/bookings/<booking_id>")
def get_booking(booking_id):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403

    with current_app.extensions["ezha_session_factory"]() as session:
        result = session.execute(
            select(Booking, PortfolioWork, User, ArtisanProfile)
            .join(PortfolioWork, PortfolioWork.id == Booking.work_id)
            .join(User, User.id == Booking.artisan_id)
            .join(ArtisanProfile, ArtisanProfile.artisan_id == User.id)
            .where(Booking.id == booking_id, Booking.customer_id == claims["sub"])
        ).first()
        if not result:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Booking not found"}}), 404
        booking, work, artisan, profile = result
        platform_fee = booking.platform_fee if booking.platform_fee is not None else split_gross_amount(booking.amount)[0]
        artisan_payout = booking.artisan_payout if booking.artisan_payout is not None else split_gross_amount(booking.amount)[1]
        data = {
            "id": booking.id,
            "work_id": work.id,
            "work_title": work.title,
            "category": work.category,
            "image_url": portfolio_image_url(work.filename, work.storage_provider),
            "artisan_id": artisan.id,
            "artisan_name": artisan.name,
            "artisan_username": artisan.username,
            "artisan_city": profile.city,
            "date": booking.service_date,
            "time": booking.service_time,
            "amount": booking.amount,
            "platform_fee": platform_fee,
            "artisan_payout": artisan_payout,
            "commission_rate": platform_commission_rate(),
            "service_mode": booking.service_mode,
            "service_address": {
                "line1": booking.service_address_line1,
                "line2": booking.service_address_line2,
                "city": booking.service_city,
                "state": booking.service_state,
                "pincode": booking.service_pincode,
            },
            "status": booking.status,
            "payment_status": booking.payment_status,
        }
    return jsonify({"success": True, "data": data}), 200


@bp.post("/bookings/<booking_id>/payment/order")
def create_booking_payment_order(booking_id):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403

    session_factory = current_app.extensions["ezha_session_factory"]
    with session_factory() as session:
        booking = session.scalar(select(Booking).where(Booking.id == booking_id, Booking.customer_id == claims["sub"]))
        if not booking:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Booking not found"}}), 404
        if booking.payment_status == "PAID":
            return jsonify({"success": False, "error": {"code": "ALREADY_PAID", "message": "This booking has already been paid"}}), 409
        amount = booking.amount
        if amount * 100 < 100:
            return jsonify({"success": False, "error": {"code": "AMOUNT_BELOW_MINIMUM", "message": "Payment amount must be at least 100 paise"}}), 400

    provider = RazorpayProvider()
    try:
        payment = provider.create_payment(amount, currency="INR", receipt=booking_id)
    except PaymentConfigurationError:
        return jsonify({"success": False, "error": {"code": "PAYMENT_NOT_CONFIGURED", "message": "Online payment is not enabled yet. Add Razorpay keys in the deployment environment settings to enable checkout."}}), 503
    except PaymentAuthenticationError:
        current_app.logger.error("Razorpay rejected the configured key pair")
        return jsonify({"success": False, "error": {"code": "PAYMENT_CREDENTIALS_REJECTED", "message": "Razorpay rejected the configured keys. Check that the key ID and secret are a matching pair from the same mode."}}), 401
    except PaymentProviderError:
        current_app.logger.exception("Razorpay order creation failed")
        return jsonify({"success": False, "error": {"code": "PAYMENT_PROVIDER_ERROR", "message": "Razorpay could not create the order. Check the server logs for the provider error."}}), 500
    except Exception:
        current_app.logger.exception("Razorpay order creation failed")
        return jsonify({"success": False, "error": {"code": "PAYMENT_PROVIDER_ERROR", "message": "Payment provider could not create an order"}}), 500

    with session_factory.begin() as session:
        booking = session.get(Booking, booking_id)
        booking.payment_order_id = payment["order_id"]
        booking.payment_status = "PAYMENT_PENDING"
    return jsonify({"success": True, "data": payment}), 201


@bp.post("/bookings/<booking_id>/payment/verify")
def verify_booking_payment(booking_id):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}), 401
    claims = service.verify_token(auth_header.split(" ", 1)[1].strip(), "access")
    if not claims:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired"}}), 401
    if claims.get("role") != "CUSTOMER":
        return jsonify({"success": False, "error": {"code": "FORBIDDEN", "message": "Customer access required"}}), 403

    payload = request.get_json(silent=True) or {}
    order_id = payload.get("razorpay_order_id", "")
    payment_id = payload.get("razorpay_payment_id", "")
    signature = payload.get("razorpay_signature", "")
    if not order_id or not payment_id or not signature:
        return jsonify({"success": False, "error": {"code": "MISSING_PAYMENT_FIELDS", "message": "Razorpay order ID, payment ID, and signature are required"}}), 400
    session_factory = current_app.extensions["ezha_session_factory"]
    with session_factory() as session:
        booking = session.scalar(select(Booking).where(Booking.id == booking_id, Booking.customer_id == claims["sub"]))
        if not booking:
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Booking not found"}}), 404
        if not booking.payment_order_id or booking.payment_order_id != order_id:
            return jsonify({"success": False, "error": {"code": "INVALID_ORDER", "message": "Payment order does not match this booking"}}), 400

    try:
        RazorpayProvider().verify_payment({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except PaymentConfigurationError:
        return jsonify({"success": False, "error": {"code": "PAYMENT_NOT_CONFIGURED", "message": "Payment verification is not configured"}}), 503
    except PaymentSignatureError:
        return jsonify({"success": False, "error": {"code": "PAYMENT_VERIFICATION_FAILED", "message": "Razorpay signature did not match; booking remains unpaid"}}), 400
    except PaymentConfigurationError:
        return jsonify({"success": False, "error": {"code": "PAYMENT_NOT_CONFIGURED", "message": "Payment verification is not configured"}}), 503
    except Exception:
        current_app.logger.exception("Razorpay signature verification failed")
        return jsonify({"success": False, "error": {"code": "PAYMENT_VERIFICATION_FAILED", "message": "Payment could not be verified"}}), 400

    with session_factory.begin() as session:
        booking = session.get(Booking, booking_id)
        booking.payment_id = payment_id
        booking.payment_status = "PAID"
        booking.status = "CONFIRMED"
        platform_fee, artisan_payout = split_gross_amount(booking.amount)
        booking.platform_fee = platform_fee
        booking.artisan_payout = artisan_payout
        booking.payout_status = "SCHEDULED"
        notify_artisan(
            session,
            booking.artisan_id,
            "PAYMENT_RECEIVED",
            "Payment received",
            f"EZHA received ₹{booking.amount}. Your share (85% after commission) is ₹{artisan_payout} and will be transferred to your registered bank account.",
            booking.id,
        )
    return jsonify({
        "success": True,
        "data": {
            "booking_id": booking_id,
            "payment_id": payment_id,
            "payment_status": "PAID",
            "status": "CONFIRMED",
            "platform_fee": platform_fee,
            "artisan_payout": artisan_payout,
        },
    }), 200
