"""Main routes for dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from config import OperationMode, ParkingConfig
from core.mode_manager import ModeManager
from core.parking_service import ParkingService
from core.state_manager import StateManager
from database.db import db
from database.models import SystemLog

main_bp = Blueprint("main", __name__)


def init_main_routes(app, state_manager: StateManager, controller=None):
    """Initialize main routes with app, state_manager, and controller."""

    @main_bp.route("/")
    def index():
        """Redirect to dashboard or login."""
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("auth.login"))

    @main_bp.route("/dashboard")
    @login_required
    def dashboard():
        """Main dashboard - different for admin and client."""
        if current_user.is_admin():
            return render_template("admin/dashboard.html", total_slots=ParkingConfig.TOTAL_SLOTS)
        return render_template("client/dashboard.html", total_slots=ParkingConfig.TOTAL_SLOTS)

    @main_bp.route("/api/status")
    @login_required
    def api_status():
        """Get parking status (protected)."""
        snapshot = state_manager.snapshot()
        stats = ParkingService.get_statistics()
        snapshot.update(stats)
        
        # Thêm thông tin chế độ
        if controller and hasattr(controller, 'mode_manager'):
            mode_info = controller.mode_manager.get_mode_info()
            snapshot.update(mode_info)
        
        # Thêm thông tin kết nối Arduino
        if controller and hasattr(controller, 'serial_client'):
            serial_client = controller.serial_client
            snapshot['arduino_connected'] = serial_client.is_connected()
            last_received = serial_client.get_last_received_time()
            if last_received:
                from datetime import UTC, datetime
                import time
                time_since = time.time() - last_received
                snapshot['arduino_last_update'] = datetime.now(UTC).isoformat()
                snapshot['arduino_update_age'] = round(time_since, 1)  # seconds
            else:
                snapshot['arduino_connected'] = False
                snapshot['arduino_last_update'] = None
                snapshot['arduino_update_age'] = None
        
        return jsonify(snapshot)

    @main_bp.route("/api/my-sessions")
    @login_required
    def api_my_sessions():
        """Get current user's parking sessions."""
        sessions = ParkingService.get_user_sessions(current_user.id, limit=20)
        return jsonify({
            "sessions": [
                {
                    "id": s.id,
                    "slot_id": s.slot_id,
                    "vehicle_plate": s.vehicle_plate,
                    "entry_time": s.entry_time.isoformat() if s.entry_time else None,
                    "exit_time": s.exit_time.isoformat() if s.exit_time else None,
                    "duration_minutes": s.duration_minutes,
                    "status": s.status,
                }
                for s in sessions
            ]
        })

    @main_bp.route("/api/history")
    @login_required
    def api_history():
        """Get parking history (admin only or own sessions)."""
        if current_user.is_admin():
            sessions = ParkingService.get_session_history(limit=100)
        else:
            sessions = ParkingService.get_user_sessions(current_user.id, limit=50)

        return jsonify({
            "sessions": [
                {
                    "id": s.id,
                    "slot_id": s.slot_id,
                    "vehicle_plate": s.vehicle_plate,
                    "user": s.user.username if s.user else None,
                    "entry_time": s.entry_time.isoformat() if s.entry_time else None,
                    "exit_time": s.exit_time.isoformat() if s.exit_time else None,
                    "duration_minutes": s.duration_minutes,
                    "status": s.status,
                }
                for s in sessions
            ]
        })

    @main_bp.route("/api/start-session", methods=["POST"])
    @login_required
    def api_start_session():
        """Start parking session."""
        data = request.get_json() or {}
        slot_id = data.get("slot_id")
        vehicle_plate = data.get("vehicle_plate")

        if slot_id is None:
            return jsonify({"error": "slot_id required"}), 400

        try:
            session = ParkingService.start_session(
                slot_id=slot_id,
                user_id=current_user.id,
                vehicle_plate=vehicle_plate,
            )
            return jsonify({
                "status": "ok",
                "session_id": session.id,
                "message": f"Đã bắt đầu đỗ tại slot {slot_id}",
            })
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @main_bp.route("/api/end-session", methods=["POST"])
    @login_required
    def api_end_session():
        """End parking session."""
        data = request.get_json() or {}
        slot_id = data.get("slot_id")

        if slot_id is None:
            return jsonify({"error": "slot_id required"}), 400

        session = ParkingService.end_session(slot_id=slot_id, user_id=current_user.id)
        if session:
            return jsonify({
                "status": "ok",
                "message": f"Đã kết thúc đỗ tại slot {slot_id}",
                "duration_minutes": session.duration_minutes,
                "fee_amount": session.fee_amount,
                "payment_status": session.payment_status,
            })
        return jsonify({"error": "Không tìm thấy session active"}), 404
    
    @main_bp.route("/api/session/<int:session_id>/fee", methods=["GET"])
    @login_required
    def api_get_fee(session_id: int):
        """Get fee for a session."""
        from database.models import ParkingSession
        session = ParkingSession.query.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Tính fee nếu chưa có
        if session.fee_amount == 0 and session.status == "completed":
            fee = ParkingService.calculate_fee(session)
            session.fee_amount = fee
            db.session.commit()
        
        return jsonify({
            "session_id": session_id,
            "fee_amount": session.fee_amount,
            "payment_status": session.payment_status,
            "duration_minutes": session.duration_minutes,
        })
    
    @main_bp.route("/api/session/<int:session_id>/pay", methods=["POST"])
    @login_required
    def api_pay_session(session_id: int):
        """Mark session as paid."""
        data = request.get_json() or {}
        payment_method = data.get("payment_method", "cash")
        
        session = ParkingService.mark_paid(session_id, payment_method, current_user.id)
        if session:
            return jsonify({
                "status": "ok",
                "message": f"Đã thanh toán {session.fee_amount:,} VNĐ",
                "payment_status": session.payment_status,
            })
        return jsonify({"error": "Session not found"}), 404
    
    @main_bp.route("/api/session/<int:session_id>/duration", methods=["GET"])
    @login_required
    def api_get_duration(session_id: int):
        """Get real-time duration for active session."""
        from database.models import ParkingSession
        session = ParkingSession.query.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if session.status == "active":
            # Tính duration real-time
            delta = datetime.now(UTC) - session.entry_time
            duration_minutes = int(delta.total_seconds() / 60)
            duration_hours = delta.total_seconds() / 3600
        else:
            duration_minutes = session.duration_minutes or 0
            duration_hours = duration_minutes / 60
        
        return jsonify({
            "session_id": session_id,
            "duration_minutes": duration_minutes,
            "duration_hours": round(duration_hours, 2),
            "status": session.status,
        })

    @main_bp.route("/admin/logs")
    @login_required
    def admin_logs():
        """View system logs (admin only)."""
        if not current_user.is_admin():
            flash("Bạn không có quyền truy cập.", "error")
            return redirect(url_for("main.dashboard"))

        logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(100).all()
        return render_template("admin/logs.html", logs=logs)

    @main_bp.route("/admin/users")
    @login_required
    def admin_users():
        """Manage users (admin only)."""
        if not current_user.is_admin():
            flash("Bạn không có quyền truy cập.", "error")
            return redirect(url_for("main.dashboard"))

        from database.models import User

        users = User.query.order_by(User.created_at.desc()).all()
        return render_template("admin/users.html", users=users)

    # ============================================
    # OPERATION MODE API
    # ============================================

    @main_bp.route("/api/mode", methods=["GET"])
    @login_required
    def api_get_mode():
        """Lấy thông tin chế độ hiện tại."""
        if not controller or not hasattr(controller, 'mode_manager'):
            return jsonify({"error": "Mode manager not available"}), 503

        mode_info = controller.mode_manager.get_mode_info()
        return jsonify(mode_info)

    @main_bp.route("/api/mode", methods=["POST"])
    @login_required
    def api_set_mode():
        """Chuyển đổi chế độ (admin only)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền thay đổi chế độ"}), 403

        if not controller or not hasattr(controller, 'mode_manager'):
            return jsonify({"error": "Mode manager not available"}), 503

        data = request.get_json() or {}
        mode = data.get("mode", "").lower()

        if mode not in (OperationMode.AUTO, OperationMode.MANUAL):
            return jsonify({"error": "Invalid mode. Use 'auto' or 'manual'"}), 400

        success = controller.mode_manager.set_mode(
            mode=mode,
            user_id=current_user.id,
            username=current_user.username,
        )

        if success:
            # Đồng bộ chế độ xuống Arduino
            controller._sync_mode_to_arduino(mode)
            
            return jsonify({
                "status": "ok",
                "mode": mode,
                "message": f"Đã chuyển sang chế độ {mode.upper()}",
            })
        return jsonify({"error": "Failed to change mode"}), 500

    # ============================================
    # MANUAL CONTROL API (Admin only)
    # ============================================
    
    @main_bp.route("/api/gate", methods=["POST"])
    @login_required
    def api_control_gate():
        """Điều khiển barrier thủ công (admin only, MANUAL mode)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền điều khiển barrier"}), 403
        
        if not controller:
            return jsonify({"error": "Controller not available"}), 503
        
        data = request.get_json() or {}
        state = data.get("state", "").lower()
        
        if state not in ("open", "closed"):
            return jsonify({"error": "Invalid state. Use 'open' or 'closed'"}), 400
        
        success = controller.manual_set_gate(state)
        if success:
            return jsonify({
                "status": "ok",
                "message": f"Đã {'mở' if state == 'open' else 'đóng'} barrier",
            })
        return jsonify({"error": "Không thể điều khiển barrier. Kiểm tra chế độ hoạt động."}), 400
    
    @main_bp.route("/api/slot/<int:slot_id>", methods=["POST"])
    @login_required
    def api_control_slot(slot_id: int):
        """Điều khiển slot thủ công (admin only, MANUAL mode)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền điều khiển slot"}), 403
        
        if not controller:
            return jsonify({"error": "Controller not available"}), 503
        
        # Slot 1 không thể set manual (từ sensor)
        if slot_id == 1:
            return jsonify({"error": "Slot 1 được điều khiển bởi sensor, không thể set manual"}), 400
        
        # Chỉ cho phép Slot 2, 3
        if slot_id < 2 or slot_id > ParkingConfig.TOTAL_SLOTS:
            return jsonify({"error": f"Slot {slot_id} không hợp lệ. Chỉ có thể set Slot 2, 3"}), 400
        
        data = request.get_json() or {}
        occupied = data.get("occupied", False)
        
        # slot_id từ URL là 1-based (1,2,3), convert sang 0-based index
        success = controller.manual_set_slot(slot_id - 1, occupied)
        if success:
            return jsonify({
                "status": "ok",
                "message": f"Đã đặt Slot {slot_id} = {'có xe' if occupied else 'trống'}",
            })
        return jsonify({"error": "Không thể điều khiển slot. Kiểm tra chế độ hoạt động."}), 400

    # ============================================
    # PRICING RULES API (Admin only)
    # ============================================
    
    @main_bp.route("/api/pricing-rules", methods=["GET"])
    @login_required
    def api_get_pricing_rules():
        """Lấy danh sách pricing rules."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền xem pricing rules"}), 403
        
        from database.models import PricingRule
        rules = PricingRule.query.order_by(PricingRule.priority.desc(), PricingRule.created_at.desc()).all()
        
        return jsonify({
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.rule_type,
                    "is_active": r.is_active,
                    "priority": r.priority,
                    "start_hour": r.start_hour,
                    "end_hour": r.end_hour,
                    "days_of_week": r.days_of_week,
                    "first_hour_fee": r.first_hour_fee,
                    "subsequent_hour_fee": r.subsequent_hour_fee,
                    "flat_rate_fee": r.flat_rate_fee,
                    "overnight_fee": r.overnight_fee,
                    "user_id": r.user_id,
                    "description": r.description,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rules
            ]
        })
    
    @main_bp.route("/api/pricing-rules", methods=["POST"])
    @login_required
    def api_create_pricing_rule():
        """Tạo pricing rule mới (admin only)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền tạo pricing rule"}), 403
        
        data = request.get_json() or {}
        
        from database.models import PricingRule
        
        rule = PricingRule(
            name=data.get("name", ""),
            rule_type=data.get("rule_type", "per_hour"),
            is_active=data.get("is_active", True),
            priority=data.get("priority", 0),
            start_hour=data.get("start_hour"),
            end_hour=data.get("end_hour"),
            days_of_week=data.get("days_of_week"),
            first_hour_fee=data.get("first_hour_fee", 0),
            subsequent_hour_fee=data.get("subsequent_hour_fee", 0),
            flat_rate_fee=data.get("flat_rate_fee", 0),
            overnight_fee=data.get("overnight_fee", 0),
            user_id=data.get("user_id"),
            description=data.get("description"),
            created_by=current_user.id,
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return jsonify({
            "status": "ok",
            "message": "Đã tạo pricing rule thành công",
            "rule_id": rule.id,
        })
    
    @main_bp.route("/api/pricing-rules/<int:rule_id>", methods=["PUT"])
    @login_required
    def api_update_pricing_rule(rule_id: int):
        """Cập nhật pricing rule (admin only)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền cập nhật pricing rule"}), 403
        
        from database.models import PricingRule
        rule = PricingRule.query.get(rule_id)
        if not rule:
            return jsonify({"error": "Pricing rule không tồn tại"}), 404
        
        data = request.get_json() or {}
        
        # Cập nhật các field
        if "name" in data:
            rule.name = data["name"]
        if "rule_type" in data:
            rule.rule_type = data["rule_type"]
        if "is_active" in data:
            rule.is_active = data["is_active"]
        if "priority" in data:
            rule.priority = data["priority"]
        if "start_hour" in data:
            rule.start_hour = data["start_hour"]
        if "end_hour" in data:
            rule.end_hour = data["end_hour"]
        if "days_of_week" in data:
            rule.days_of_week = data["days_of_week"]
        if "first_hour_fee" in data:
            rule.first_hour_fee = data["first_hour_fee"]
        if "subsequent_hour_fee" in data:
            rule.subsequent_hour_fee = data["subsequent_hour_fee"]
        if "flat_rate_fee" in data:
            rule.flat_rate_fee = data["flat_rate_fee"]
        if "overnight_fee" in data:
            rule.overnight_fee = data["overnight_fee"]
        if "user_id" in data:
            rule.user_id = data["user_id"]
        if "description" in data:
            rule.description = data["description"]
        
        rule.updated_at = datetime.now(UTC)
        db.session.commit()
        
        return jsonify({
            "status": "ok",
            "message": "Đã cập nhật pricing rule thành công",
        })
    
    @main_bp.route("/api/pricing-rules/<int:rule_id>", methods=["DELETE"])
    @login_required
    def api_delete_pricing_rule(rule_id: int):
        """Xóa pricing rule (admin only)."""
        if not current_user.is_admin():
            return jsonify({"error": "Chỉ admin mới có quyền xóa pricing rule"}), 403
        
        from database.models import PricingRule
        rule = PricingRule.query.get(rule_id)
        if not rule:
            return jsonify({"error": "Pricing rule không tồn tại"}), 404
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({
            "status": "ok",
            "message": "Đã xóa pricing rule thành công",
        })
    
    @main_bp.route("/admin/pricing")
    @login_required
    def admin_pricing():
        """Quản lý pricing rules (admin only)."""
        if not current_user.is_admin():
            flash("Bạn không có quyền truy cập.", "error")
            return redirect(url_for("main.dashboard"))
        
        return render_template("admin/pricing.html")
    
    app.register_blueprint(main_bp)

