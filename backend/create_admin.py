from __future__ import annotations

from getpass import getpass

from sqlalchemy import or_, select
from werkzeug.security import generate_password_hash

from backend.app import create_app
from backend.app.models.user import User


def main() -> None:
    app = create_app()
    username = input("Admin username: ").strip().lower()
    email = input("Admin email: ").strip().lower()
    name = input("Admin display name: ").strip()
    password = getpass("Admin password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")

    if not username or not email or not name:
        raise SystemExit("Username, email, and display name are required.")
    if len(password) < 12:
        raise SystemExit("Choose a password with at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with app.app_context():
        session_factory = app.extensions["ezha_session_factory"]
        with session_factory.begin() as session:
            existing = session.scalar(select(User.id).where(or_(User.username == username, User.email == email)))
            if existing:
                raise SystemExit("That username or email is already registered.")
            session.add(User(
                username=username,
                email=email,
                name=name,
                password_hash=generate_password_hash(password),
                role="ADMIN",
            ))
    print("Admin account created.")


if __name__ == "__main__":
    main()