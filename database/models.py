"""Database models for Smart Parking System."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import db


class User(UserMixin, db.Model):
    """User model with authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client")  # admin, client
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    last_login = db.Column(db.DateTime)

    # Relationships
    parking_sessions = db.relationship("ParkingSession", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class ParkingSession(db.Model):
    """Parking session record."""

    __tablename__ = "parking_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    slot_id = db.Column(db.Integer, nullable=False)  # 0, 1, 2...
    vehicle_plate = db.Column(db.String(20))  # Biển số xe (nếu có)
    entry_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    exit_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)  # Thời gian đỗ (phút)
    status = db.Column(db.String(20), default="active")  # active, completed, cancelled
    notes = db.Column(db.Text)
    
    # Payment fields
    fee_amount = db.Column(db.Integer, default=0)  # Phí đỗ xe (VNĐ)
    payment_status = db.Column(db.String(20), default="pending")  # pending, paid, free
    payment_time = db.Column(db.DateTime)  # Thời điểm thanh toán
    payment_method = db.Column(db.String(20))  # cash, card, online, free

    # Relationships
    user = db.relationship("User", back_populates="parking_sessions")

    def complete(self) -> None:
        """Mark session as completed."""
        self.exit_time = datetime.now(UTC)
        if self.entry_time:
            delta = self.exit_time - self.entry_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        self.status = "completed"

    def __repr__(self) -> str:
        return f"<ParkingSession {self.id} - Slot {self.slot_id}>"


class PricingRule(db.Model):
    """Pricing rule for parking fees - Admin configurable."""

    __tablename__ = "pricing_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Tên quy tắc (ví dụ: "Giờ cao điểm sáng")
    rule_type = db.Column(db.String(50), nullable=False)  # time_based, flat_rate, per_hour, overnight, custom
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=0)  # Độ ưu tiên (số càng cao càng ưu tiên)
    
    # Time-based pricing (theo khung giờ)
    start_hour = db.Column(db.Integer)  # Giờ bắt đầu (0-23)
    end_hour = db.Column(db.Integer)  # Giờ kết thúc (0-23)
    days_of_week = db.Column(db.String(20))  # "0,1,2,3,4,5,6" (0=Monday, 6=Sunday), null = tất cả
    
    # Pricing values
    first_hour_fee = db.Column(db.Integer, default=0)  # Phí giờ đầu (VNĐ)
    subsequent_hour_fee = db.Column(db.Integer, default=0)  # Phí mỗi giờ tiếp theo (VNĐ)
    flat_rate_fee = db.Column(db.Integer, default=0)  # Phí đồng giá (VNĐ) - dùng khi rule_type = "flat_rate"
    overnight_fee = db.Column(db.Integer, default=0)  # Phí qua đêm (VNĐ) - dùng khi rule_type = "overnight"
    
    # Custom pricing (theo user)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # null = áp dụng cho tất cả
    
    # Metadata
    description = db.Column(db.Text)  # Mô tả quy tắc
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Admin tạo rule

    def __repr__(self) -> str:
        return f"<PricingRule {self.name} ({self.rule_type})>"


class SystemLog(db.Model):
    """System event log."""

    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # gate_open, gate_close, slot_change, etc.
    message = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    meta_data = db.Column(db.JSON)  # Additional data as JSON (renamed from 'metadata' - reserved name)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SystemLog {self.event_type} at {self.created_at}>"

