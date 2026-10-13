from __future__ import annotations

from pathlib import Path

from flask import Flask
from sqlalchemy import create_engine, or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from backend.app.models.user import ArtisanProfile, Base, User


DEMO_USERS = (
    {"username": "customer", "email": "customer@demo.ezha", "name": "Demo Customer", "password": "demo123", "role": "CUSTOMER"},
    {"username": "ananya", "email": "vendor@demo.ezha", "name": "Ananya", "password": "demo123", "role": "ARTISAN"},
    {"username": "admin", "email": "admin@demo.ezha", "name": "Demo Admin", "password": "demo123", "role": "ADMIN"},
)


def initialize_database(app: Flask) -> None:
    database_url = app.config["DATABASE_URL"]
    if not isinstance(database_url, str) or not database_url.strip():
        raise RuntimeError("DATABASE_URL is empty. Set it to a PostgreSQL connection string in Render.")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend in {"postgres", "postgresql"} and not url.host:
        raise RuntimeError(
            "DATABASE_URL must include a PostgreSQL host. In Render, use the Supabase Database connection string, not SUPABASE_URL."
        )
    if backend not in {"sqlite", "postgres", "postgresql"}:
        raise RuntimeError(
            "DATABASE_URL must be a sqlite:///... URL locally or a postgresql://... Supabase connection string."
        )

    connect_args = {}
    if backend == "sqlite":
        connect_args["check_same_thread"] = False
        if url.database not in (None, "", ":memory:"):
            Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    dialect_name = engine.dialect.name
    is_postgres = dialect_name in {"postgres", "postgresql"} or dialect_name.startswith("postgres")
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    booking_columns = {column["name"] for column in inspect(engine).get_columns("bookings")}
    booking_alters = {
        "payment_order_id": "ALTER TABLE bookings ADD COLUMN payment_order_id VARCHAR(100)",
        "payment_id": "ALTER TABLE bookings ADD COLUMN payment_id VARCHAR(100)",
        "service_mode": "ALTER TABLE bookings ADD COLUMN service_mode VARCHAR(16) NOT NULL DEFAULT 'DOORSTEP'",
        "service_address_line1": "ALTER TABLE bookings ADD COLUMN service_address_line1 VARCHAR(200) NOT NULL DEFAULT ''",
        "service_address_line2": "ALTER TABLE bookings ADD COLUMN service_address_line2 VARCHAR(200) NOT NULL DEFAULT ''",
        "service_city": "ALTER TABLE bookings ADD COLUMN service_city VARCHAR(100) NOT NULL DEFAULT ''",
        "service_state": "ALTER TABLE bookings ADD COLUMN service_state VARCHAR(100) NOT NULL DEFAULT ''",
        "service_pincode": "ALTER TABLE bookings ADD COLUMN service_pincode VARCHAR(10) NOT NULL DEFAULT ''",
        "platform_fee": "ALTER TABLE bookings ADD COLUMN platform_fee INTEGER",
        "artisan_payout": "ALTER TABLE bookings ADD COLUMN artisan_payout INTEGER",
        "payout_status": "ALTER TABLE bookings ADD COLUMN payout_status VARCHAR(24) NOT NULL DEFAULT 'UNPAID'",
    }
    with engine.begin() as connection:
        for column_name, statement in booking_alters.items():
            if column_name not in booking_columns:
                connection.execute(text(statement))
    booking_columns = {column["name"] for column in inspect(engine).get_columns("bookings")}
    acceptance_deadline_type = "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME"
    booking_extra = {
        "acceptance_deadline": f"ALTER TABLE bookings ADD COLUMN acceptance_deadline {acceptance_deadline_type}",
        "artisan_decision": "ALTER TABLE bookings ADD COLUMN artisan_decision VARCHAR(24) NOT NULL DEFAULT 'PENDING'",
    }
    with engine.begin() as connection:
        for column_name, statement in booking_extra.items():
            if column_name not in booking_columns:
                connection.execute(text(statement))
    artisan_columns = {column["name"] for column in inspect(engine).get_columns("artisan_profiles")}
    artisan_alters = {
        "account_holder_name": "ALTER TABLE artisan_profiles ADD COLUMN account_holder_name VARCHAR(160) NOT NULL DEFAULT ''",
        "account_number": "ALTER TABLE artisan_profiles ADD COLUMN account_number VARCHAR(32) NOT NULL DEFAULT ''",
        "ifsc_code": "ALTER TABLE artisan_profiles ADD COLUMN ifsc_code VARCHAR(11) NOT NULL DEFAULT ''",
    }
    with engine.begin() as connection:
        for column_name, statement in artisan_alters.items():
            if column_name not in artisan_columns:
                connection.execute(text(statement))
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    bool_default = "FALSE" if is_postgres else "0"
    user_alters = {
        "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT ''",
        "email_verified": f"ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT {bool_default}",
        "phone_verified": f"ALTER TABLE users ADD COLUMN phone_verified BOOLEAN NOT NULL DEFAULT {bool_default}",
    }
    with engine.begin() as connection:
        for column_name, statement in user_alters.items():
            if column_name not in user_columns:
                connection.execute(text(statement))
    portfolio_columns = {column["name"] for column in inspect(engine).get_columns("portfolio_works")}
    if "storage_provider" not in portfolio_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE portfolio_works ADD COLUMN storage_provider VARCHAR(16) NOT NULL DEFAULT 'local'"))
    app.extensions["ezha_engine"] = engine
    app.extensions["ezha_session_factory"] = session_factory

    if app.config.get("SEED_DEMO_USERS", app.config.get("APP_ENV", "development") != "production"):
        with session_factory.begin() as session:
            for demo_user in DEMO_USERS:
                existing = session.scalar(select(User).where(or_(User.username == demo_user["username"], User.email == demo_user["email"])))
                if existing is None:
                    existing = User(
                        username=demo_user["username"],
                        email=demo_user["email"],
                        name=demo_user["name"],
                        password_hash=generate_password_hash(demo_user["password"]),
                        role=demo_user["role"],
                    )
                    session.add(existing)
                    session.flush()
                if demo_user["role"] == "ARTISAN":
                    profile = session.get(ArtisanProfile, existing.id)
                    if profile is None:
                        session.add(
                            ArtisanProfile(
                                artisan_id=existing.id,
                                city="Bengaluru",
                                category="MAKEUP",
                                account_holder_name="Ananya Demo",
                                account_number="123456789012",
                                ifsc_code="HDFC0001234",
                            )
                        )
                    elif not profile.account_number:
                        profile.account_holder_name = "Ananya Demo"
                        profile.account_number = "123456789012"
                        profile.ifsc_code = "HDFC0001234"