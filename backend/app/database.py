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
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    url = make_url(database_url)
    connect_args = {}
    if url.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
        if url.database not in (None, "", ":memory:"):
            Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    booking_columns = {column["name"] for column in inspect(engine).get_columns("bookings")}
    with engine.begin() as connection:
        if "payment_order_id" not in booking_columns:
            connection.execute(text("ALTER TABLE bookings ADD COLUMN payment_order_id VARCHAR(100)"))
        if "payment_id" not in booking_columns:
            connection.execute(text("ALTER TABLE bookings ADD COLUMN payment_id VARCHAR(100)"))
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
                        session.add(ArtisanProfile(artisan_id=existing.id, city="Bengaluru", category="MAKEUP"))