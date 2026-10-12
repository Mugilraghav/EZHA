from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ArtisanProfile(Base):
    __tablename__ = "artisan_profiles"

    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    city: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="MAKEUP", nullable=False)


class PortfolioWork(Base):
    __tablename__ = "portfolio_works"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(16), default="local", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    work_id: Mapped[str] = mapped_column(ForeignKey("portfolio_works.id", ondelete="CASCADE"), index=True, nullable=False)
    service_date: Mapped[str] = mapped_column(String(10), nullable=False)
    service_time: Mapped[str] = mapped_column(String(5), nullable=False)
    notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(24), default="UNPAID", nullable=False)
    payment_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    payment_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)