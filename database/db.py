"""Database configuration."""

from __future__ import annotations

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app: Flask) -> None:
    """Initialize database with app."""
    db.init_app(app)

    with app.app_context():
        # Create all tables
        db.create_all()

        # Create default admin user if not exists
        from database.models import User

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@parking.local",
                role="admin",
                full_name="System Administrator",
                is_active=True,
            )
            admin.set_password("admin123")  # Change in production!
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user: admin/admin123")

