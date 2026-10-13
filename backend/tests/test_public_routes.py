from pathlib import Path

import pytest

from backend.app import create_app as app_factory


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-secret"
    DATABASE_URL = "sqlite:///:memory:"
    RAZORPAY_KEY_ID = ""
    RAZORPAY_KEY_SECRET = ""


def create_app(config_class=TestConfig):
    return app_factory(config_class)


def test_homepage_renders_ezha_branding():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"EZHA" in response.data
    assert b"Your Style. Your Artist. Your Signature." in response.data
    assert b'/static/assets/ezha-logo.png' in response.data
    logo = client.get('/static/assets/ezha-logo.png')
    assert logo.status_code == 200
    assert logo.mimetype == 'image/png'


def test_landing_page_primary_controls_have_working_destinations():
    response = create_app().test_client().get("/")

    assert response.status_code == 200
    assert b'id="landing-search-form"' in response.data
    assert b'data-focus-search' in response.data
    assert b'href="/login"' in response.data
    assert b'href="/register"' in response.data
    assert b'href="/customer/services?service_id=svc_001"' in response.data


def test_registered_artisan_and_categorized_work_appear_to_customers(tmp_path):
    from io import BytesIO

    app = create_app()
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    client = app.test_client()

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "username": "artist_meera",
            "email": "meera.artist@example.com",
            "password": "artist-password",
            "name": "Meera Artist",
            "role": "ARTISAN",
            "city": "Chennai",
            "category": "MEHENDI",
        },
    )
    assert registration.status_code == 201
    artisan_id = registration.get_json()["data"]["id"]

    artisan_login = client.post(
        "/api/v1/auth/login",
        json={"username": "artist_meera", "password": "artist-password", "role": "ARTISAN"},
    )
    artisan_token = artisan_login.get_json()["data"]["access_token"]
    upload = client.post(
        "/api/v1/artisan/portfolio",
        headers={"Authorization": f"Bearer {artisan_token}"},
        data={
            "title": "Bridal henna design",
            "category": "MEHENDI",
            "price": "4500",
            "caption": "Intricate bridal mehendi",
            "file": (BytesIO(b"portfolio image"), "mehendi.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201

    customer_login = client.post(
        "/api/v1/auth/login",
        json={"username": "customer", "password": "demo123", "role": "CUSTOMER"},
    )
    customer_token = customer_login.get_json()["data"]["access_token"]
    listings = client.get(
        "/api/v1/customers/artisans?category=MEHENDI",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert listings.status_code == 200
    artist = next(row for row in listings.get_json()["data"]["artisans"] if row["id"] == artisan_id)
    assert artist["username"] == "artist_meera"
    assert artist["city"] == "Chennai"
    assert artist["works"][0]["category"] == "MEHENDI"
    assert artist["works"][0]["price"] == 4500
    image_response = client.get(artist["works"][0]["image_url"])
    assert image_response.status_code == 200

    work_id = artist["works"][0]["id"]
    booking_response = client.post(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"work_id": work_id, "date": "2026-12-12", "time": "11:00", "notes": "Bridal mehendi"},
    )
    assert booking_response.status_code == 201
    booking_id = booking_response.get_json()["data"]["id"]
    checkout = client.get(f"/api/v1/bookings/{booking_id}", headers={"Authorization": f"Bearer {customer_token}"})
    assert checkout.status_code == 200
    assert checkout.get_json()["data"]["amount"] == 4500
    payment_order = client.post(
        f"/api/v1/bookings/{booking_id}/payment/order",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert payment_order.status_code == 503
    assert payment_order.get_json()["error"]["code"] == "PAYMENT_NOT_CONFIGURED"

    artisan_dashboard = client.get(
        "/api/v1/artisan/dashboard",
        headers={"Authorization": f"Bearer {artisan_token}"},
    )
    assert any(order["id"] == booking_id for order in artisan_dashboard.get_json()["data"]["orders"])

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "demo123", "role": "ADMIN"},
    )
    admin_token = admin_login.get_json()["data"]["access_token"]
    dashboard = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert dashboard.get_json()["data"]["kpis"]["artisans"] >= 2
    assert dashboard.get_json()["data"]["kpis"]["orders"] >= 3
    assert any(artisan["id"] == artisan_id for artisan in dashboard.get_json()["data"]["artisan_list"])


def test_marketplace_pages_are_available():
    app = create_app()
    client = app.test_client()

    for route, expected in [
        ("/explore", b"Explore"),
        ("/category", b"Category"),
        ("/vendor", b"Vendor"),
    ]:
        response = client.get(route)
        assert response.status_code == 200
        assert expected in response.data


def test_booking_pages_are_available():
    app = create_app()
    client = app.test_client()

    for route, expected in [
        ("/booking", b"Booking"),
        ("/checkout", b"Checkout"),
    ]:
        response = client.get(route)
        assert response.status_code == 200
        assert expected in response.data

    assert b'id="booking-form"' in client.get("/booking").data
    assert b'id="pay-button"' in client.get("/checkout").data


def test_vendor_and_admin_pages_are_available():
    app = create_app()
    client = app.test_client()

    for route, expected in [
        ("/vendor/dashboard", b"Vendor Dashboard"),
        ("/admin/dashboard", b"Admin Dashboard"),
    ]:
        response = client.get(route)
        assert response.status_code == 200
        assert expected in response.data


def test_payment_provider_abstraction_is_defined():
    from backend.app.services.payments import PaymentProvider, RazorpayProvider

    assert issubclass(RazorpayProvider, PaymentProvider)
    assert RazorpayProvider().provider_name == "razorpay"


def test_auth_and_rbac_routes_exist():
    app = create_app()
    client = app.test_client()

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "securepass", "name": "New User"},
    )
    assert register_response.status_code in (200, 201)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123"},
    )
    assert login_response.status_code == 200
    data = login_response.get_json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert b"Login successful" in login_response.data

    customer_response = client.get("/api/v1/customers/me")
    assert customer_response.status_code == 401

    vendor_response = client.get("/api/v1/vendors")
    assert vendor_response.status_code == 401

    admin_response = client.get("/api/v1/admin/dashboard")
    assert admin_response.status_code == 401


def test_auth_rbac_enforces_permissions():
    app = create_app()
    client = app.test_client()

    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123"},
    )
    customer_token = customer_login.get_json()["data"]["access_token"]

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.ezha", "password": "demo123"},
    )
    admin_token = admin_login.get_json()["data"]["access_token"]

    unauthorized_customer = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert unauthorized_customer.status_code == 403

    authorized_admin = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert authorized_admin.status_code == 200


def test_vendor_catalog_is_seeded_and_accessible():
    app = create_app()
    client = app.test_client()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123"},
    )
    token = login.get_json()["data"]["access_token"]

    response = client.get(
        "/api/v1/vendors",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "vendors" in payload["data"]
    assert any(v["name"] == "Aditi Mehra" for v in payload["data"]["vendors"])


def test_service_catalog_is_available():
    app = create_app()
    client = app.test_client()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123"},
    )
    token = login.get_json()["data"]["access_token"]

    response = client.get(
        "/api/v1/services",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "services" in payload["data"]
    assert any(s["title"] == "Bridal Makeup Trial" for s in payload["data"]["services"])


def test_vendor_detail_and_booking_flow():
    app = create_app()
    client = app.test_client()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123"},
    )
    token = login.get_json()["data"]["access_token"]

    vendor_response = client.get(
        "/api/v1/vendors/vend_001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert vendor_response.status_code == 200
    vendor_payload = vendor_response.get_json()
    assert vendor_payload["success"] is True
    assert vendor_payload["data"]["vendor"]["name"] == "Aditi Mehra"

    service_response = client.get(
        "/api/v1/services/svc_001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert service_response.status_code == 200
    service_payload = service_response.get_json()
    assert service_payload["data"]["service"]["title"] == "Bridal Makeup Trial"

    booking_response = client.post(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vendor_id": "vend_001",
            "service_id": "svc_001",
            "date": "2026-11-15",
            "time": "10:30",
            "notes": "Soft glam bridal look",
            "guest_count": 2,
        },
    )
    assert booking_response.status_code == 201
    booking_payload = booking_response.get_json()
    assert booking_payload["success"] is True
    assert booking_payload["data"]["vendor_id"] == "vend_001"
    assert booking_payload["data"]["service_id"] == "svc_001"


def test_role_registration_and_login_are_role_specific():
    app = create_app()
    client = app.test_client()

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "username": "mira_artist",
            "email": "mira.artist@example.com",
            "password": "studio-pass-123",
            "name": "Mira Artist",
            "role": "ARTISAN",
        },
    )
    assert registration.status_code == 201
    assert registration.get_json()["data"]["role"] == "ARTISAN"

    artisan_login = client.post(
        "/api/v1/auth/login",
        json={"username": "mira_artist", "password": "studio-pass-123", "role": "ARTISAN"},
    )
    assert artisan_login.status_code == 200
    assert artisan_login.get_json()["data"]["user"]["role"] == "ARTISAN"

    wrong_portal_login = client.post(
        "/api/v1/auth/login",
        json={"username": "mira_artist", "password": "studio-pass-123", "role": "CUSTOMER"},
    )
    assert wrong_portal_login.status_code == 403

    admin_registration = client.post(
        "/api/v1/auth/register",
        json={"username": "fake_admin", "password": "not-allowed", "role": "ADMIN"},
    )
    assert admin_registration.status_code == 400


def test_role_portal_pages_and_artisan_dashboard_access():
    app = create_app()
    client = app.test_client()

    for route in ("/login", "/register", "/customer/services", "/artisan/dashboard"):
        assert client.get(route).status_code == 200

    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@demo.ezha", "password": "demo123", "role": "CUSTOMER"},
    )
    customer_token = customer_login.get_json()["data"]["access_token"]
    denied = client.get(
        "/api/v1/artisan/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert denied.status_code == 403

    artisan_login = client.post(
        "/api/v1/auth/login",
        json={"email": "vendor@demo.ezha", "password": "demo123", "role": "ARTISAN"},
    )
    artisan_token = artisan_login.get_json()["data"]["access_token"]
    dashboard = client.get(
        "/api/v1/artisan/dashboard",
        headers={"Authorization": f"Bearer {artisan_token}"},
    )
    assert dashboard.status_code == 200
    assert "orders" in dashboard.get_json()["data"]
    assert "payments" in dashboard.get_json()["data"]


def test_artisan_can_upload_portfolio_image(tmp_path):
    from io import BytesIO

    app = create_app()
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "ananya", "password": "demo123", "role": "ARTISAN"},
    )
    token = login.get_json()["data"]["access_token"]

    response = client.post(
        "/api/v1/artisan/portfolio",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Editorial bridal look",
            "category": "MAKEUP",
            "price": "8500",
            "caption": "Editorial bridal look",
            "file": (BytesIO(b"fake image bytes"), "look.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["caption"] == "Editorial bridal look"
    assert (tmp_path / response.get_json()["data"]["filename"]).exists()


def test_artisan_upload_uses_supabase_storage_when_configured(tmp_path, monkeypatch):
    from io import BytesIO

    app = create_app()
    app.config.update(
        UPLOAD_FOLDER=str(tmp_path),
        SUPABASE_URL="https://ezha-project.supabase.co",
        SUPABASE_STORAGE_BUCKET="artisan-work",
        SUPABASE_SERVICE_ROLE_KEY="server-only-test-secret",
    )
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("backend.app.services.storage.requests.post", fake_post)
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "ananya", "password": "demo123", "role": "ARTISAN"},
    )
    token = login.get_json()["data"]["access_token"]
    response = client.post(
        "/api/v1/artisan/portfolio",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Supabase test work",
            "category": "MAKEUP",
            "price": "2500",
            "file": (BytesIO(b"image bytes"), "work.png", "image/png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    result = response.get_json()["data"]
    image_route = client.get(
        f"/api/v1/artisan/portfolio/{result['filename']}",
        follow_redirects=False,
    )
    assert calls["url"].startswith("https://ezha-project.supabase.co/storage/v1/object/artisan-work/portfolio/")
    assert calls["headers"]["Authorization"] == "Bearer server-only-test-secret"
    assert result["url"].startswith("https://ezha-project.supabase.co/storage/v1/object/public/artisan-work/portfolio/")
    assert image_route.status_code == 302
    assert image_route.headers["Location"] == result["url"]
    assert not list(tmp_path.iterdir())


def test_admin_monitoring_api_is_role_protected():
    app = create_app()
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "demo123", "role": "ADMIN"},
    )
    token = login.get_json()["data"]["access_token"]
    response = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert {"customers", "artisans", "orders", "revenue"} <= response.get_json()["data"]["kpis"].keys()


def test_registered_customer_persists_with_hashed_password(tmp_path):
    import sqlite3

    database_path = tmp_path / "ezha-test.db"

    class DatabaseTestConfig:
        TESTING = True
        SECRET_KEY = "test-secret"
        JWT_SECRET_KEY = "test-secret"
        DATABASE_URL = f"sqlite:///{database_path}"

    app = create_app(DatabaseTestConfig)
    response = app.test_client().post(
        "/api/v1/auth/register",
        json={
            "username": "persistent_customer",
            "email": "persistent@example.com",
            "password": "customer-password",
            "name": "Persistent Customer",
            "role": "CUSTOMER",
        },
    )
    assert response.status_code == 201

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT username, email, role, password_hash FROM users WHERE username = ?",
            ("persistent_customer",),
        ).fetchone()

    assert row is not None
    assert row[:3] == ("persistent_customer", "persistent@example.com", "CUSTOMER")
    assert row[3] != "customer-password"
    assert row[3].startswith("scrypt:") or row[3].startswith("pbkdf2:")

    restarted_app = create_app(DatabaseTestConfig)
    login = restarted_app.test_client().post(
        "/api/v1/auth/login",
        json={"username": "persistent_customer", "password": "customer-password", "role": "CUSTOMER"},
    )
    assert login.status_code == 200


def test_production_configuration_does_not_seed_demo_accounts():
    class ProductionTestConfig(TestConfig):
        APP_ENV = "production"
        SEED_DEMO_USERS = False
        SECRET_KEY = "test-production-secret-not-for-real-use"
        JWT_SECRET_KEY = "test-production-secret-not-for-real-use"

    app = app_factory(ProductionTestConfig)
    response = app.test_client().post(
        "/api/v1/auth/login",
        json={"username": "customer", "password": "demo123", "role": "CUSTOMER"},
    )
    demo_endpoint = app.test_client().get("/api/v1/auth/demo")

    assert response.status_code == 401
    assert demo_endpoint.status_code == 404


def test_render_blueprint_uses_repository_root_requirements():
    repository_root = Path(__file__).resolve().parents[2]
    render_config = (repository_root / "render.yaml").read_text()

    assert (repository_root / "requirements.txt").is_file()
    assert "rootDir: ." in render_config
    assert "pip install -r requirements.txt" in render_config


def test_postgres_database_url_without_host_has_actionable_error():
    class MissingDatabaseHostConfig(TestConfig):
        DATABASE_URL = "postgresql://postgres:example@/postgres"

    with pytest.raises(RuntimeError, match="DATABASE_URL must include a PostgreSQL host"):
        app_factory(MissingDatabaseHostConfig)
