"""Khởi tạo Flask app phục vụ dashboard."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request
from flask_login import LoginManager

from config import ParkingConfig, WebConfig
from core.state_manager import StateManager
from database.db import db, init_db
from database.models import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để truy cập."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Load user for Flask-Login."""
    return User.query.get(int(user_id))


def create_app(state_manager: StateManager, controller=None) -> Flask:
    """Create and configure Flask app."""
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///parking.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    init_db(app)
    login_manager.init_app(app)

    # Register blueprints
    from auth import auth_bp
    from web.main_routes import init_main_routes

    app.register_blueprint(auth_bp)
    init_main_routes(app, state_manager, controller=controller)

    # ============================================
    # LEGACY API ENDPOINTS (for backward compatibility)
    # ============================================

    @app.get("/status")
    def status():
        """Legacy status endpoint (public for now, can be protected later)."""
        return jsonify(state_manager.snapshot())

    @app.post("/api/gate")
    def manual_gate():
        """Điều khiển gate thủ công (protected in production)."""
        if not controller:
            return jsonify({"error": "Controller not available"}), 503

        state = request.args.get("state", "").lower()
        if state not in ("open", "closed"):
            return jsonify({"error": "Invalid state. Use 'open' or 'closed'"}), 400

        success = controller.manual_set_gate(state)
        if success:
            return jsonify({"status": "ok", "gate": state})
        return jsonify({"error": "Failed to set gate"}), 500

    @app.post("/api/slot")
    def manual_slot():
        """Đặt trạng thái slot thủ công (protected in production)."""
        if not controller:
            return jsonify({"error": "Controller not available"}), 503

        try:
            slot_index = int(request.args.get("index", -1))
            occupied = request.args.get("occupied", "false").lower() == "true"
        except ValueError:
            return jsonify({"error": "Invalid parameters"}), 400

        success = controller.manual_set_slot(slot_index, occupied)
        if success:
            return jsonify({"status": "ok", "slot": slot_index, "occupied": occupied})
        return jsonify({"error": "Failed to set slot"}), 500

    @app.post("/api/buzzer")
    def manual_buzzer():
        """Kích hoạt buzzer thủ công (protected in production)."""
        if not controller:
            return jsonify({"error": "Controller not available"}), 503

        try:
            duration = float(request.args.get("duration", 0.2))
        except ValueError:
            duration = 0.2

        success = controller.manual_trigger_buzzer(duration)
        if success:
            return jsonify({"status": "ok", "duration": duration})
        return jsonify({"error": "Buzzer not available"}), 503

    @app.get("/api/health")
    def health_check():
        """Health check endpoint."""
        snapshot = state_manager.snapshot()
        last_update = state_manager.last_update()

        from datetime import UTC, datetime

        now = datetime.now(UTC)
        time_since_update = (now - last_update).total_seconds()

        is_healthy = time_since_update < 10

        return jsonify({
            "status": "healthy" if is_healthy else "degraded",
            "last_update": last_update.isoformat(),
            "seconds_since_update": round(time_since_update, 2),
            "slots": {
                "total": ParkingConfig.TOTAL_SLOTS,
                "free": snapshot.get("free", 0),
                "occupied": ParkingConfig.TOTAL_SLOTS - snapshot.get("free", 0),
            },
            "gate": snapshot.get("gate", "unknown"),
        })

    @app.get("/api/stats")
    def get_stats():
        """Thống kê hệ thống."""
        snapshot = state_manager.snapshot()
        total = ParkingConfig.TOTAL_SLOTS
        free = snapshot.get("free", 0)
        occupied = total - free

        return jsonify({
            "total_slots": total,
            "free_slots": free,
            "occupied_slots": occupied,
            "usage_rate": round((occupied / total * 100) if total > 0 else 0, 2),
            "gate_status": snapshot.get("gate", "unknown"),
            "last_update": snapshot.get("last_update"),
            "has_errors": len(snapshot.get("errors", [])) > 0,
        })

    return app
