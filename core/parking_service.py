"""Parking service for managing sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional

from database.db import db
from database.models import ParkingSession, PricingRule, SystemLog, User


class ParkingService:
    """Service for managing parking sessions."""

    @staticmethod
    def start_session(slot_id: int, user_id: Optional[int] = None, vehicle_plate: Optional[str] = None) -> ParkingSession:
        """Start a new parking session."""
        # Check if slot already has active session
        active = ParkingSession.query.filter_by(slot_id=slot_id, status="active").first()
        if active:
            raise ValueError(f"Slot {slot_id} đã có xe đỗ.")

        session = ParkingSession(
            user_id=user_id,
            slot_id=slot_id,
            vehicle_plate=vehicle_plate,
            entry_time=datetime.now(UTC),
            status="active",
        )
        db.session.add(session)

        # Log event
        log = SystemLog(
            event_type="session_start",
            message=f"Xe bắt đầu đỗ tại slot {slot_id}",
            user_id=user_id,
            meta_data={"slot_id": slot_id, "vehicle_plate": vehicle_plate},
        )
        db.session.add(log)

        db.session.commit()
        return session

    @staticmethod
    def end_session(slot_id: int, user_id: Optional[int] = None) -> Optional[ParkingSession]:
        """End parking session for a slot."""
        session = ParkingSession.query.filter_by(slot_id=slot_id, status="active").first()
        if not session:
            return None

        session.complete()
        
        # Tự động tính tiền khi kết thúc session
        fee_amount = ParkingService.calculate_fee(session)
        session.fee_amount = fee_amount
        session.payment_status = "pending"  # Mặc định chưa thanh toán

        # Log event
        db.session.add(SystemLog(
            event_type="session_end",
            message=f"Xe rời khỏi slot {slot_id}. Phí: {fee_amount:,} VNĐ",
            user_id=user_id,
            meta_data={
                "slot_id": slot_id,
                "duration_minutes": session.duration_minutes,
                "fee_amount": fee_amount,
            },
        ))

        db.session.commit()
        return session

    @staticmethod
    def get_active_sessions() -> List[ParkingSession]:
        """Get all active parking sessions."""
        return ParkingSession.query.filter_by(status="active").order_by(ParkingSession.entry_time.desc()).all()

    @staticmethod
    def get_user_sessions(user_id: int, limit: int = 10) -> List[ParkingSession]:
        """Get parking sessions for a user."""
        return (
            ParkingSession.query.filter_by(user_id=user_id)
            .order_by(ParkingSession.entry_time.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_session_history(limit: int = 50) -> List[ParkingSession]:
        """Get recent parking session history."""
        return ParkingSession.query.order_by(ParkingSession.entry_time.desc()).limit(limit).all()

    @staticmethod
    def calculate_fee(session: ParkingSession, user_id: Optional[int] = None) -> int:
        """
        Tính phí đỗ xe dựa trên pricing rules do admin cấu hình.
        
        Logic:
        1. Tìm pricing rules phù hợp (theo thời gian, user, priority)
        2. Áp dụng rule có priority cao nhất
        3. Tính phí theo rule_type:
           - time_based: Theo khung giờ (start_hour - end_hour)
           - flat_rate: Đồng giá
           - per_hour: Theo giờ (first_hour_fee + subsequent_hour_fee)
           - overnight: Qua đêm
           - custom: Theo user cụ thể
        """
        if not session.duration_minutes or not session.entry_time:
            return 0
        
        # Lấy pricing rules
        rules = ParkingService._get_applicable_rules(session, user_id)
        
        if not rules:
            # Fallback: giá mặc định
            hours = (session.duration_minutes + 59) // 60
            if hours == 0:
                return 0
            elif hours == 1:
                return 10000
            else:
                return 10000 + (hours - 1) * 5000
        
        # Áp dụng rule có priority cao nhất
        rule = rules[0]
        return ParkingService._apply_pricing_rule(rule, session)
    
    @staticmethod
    def _get_applicable_rules(session: ParkingSession, user_id: Optional[int] = None) -> List:
        """Lấy danh sách pricing rules phù hợp với session."""
        from database.models import PricingRule
        
        entry_time = session.entry_time
        entry_hour = entry_time.hour
        entry_weekday = entry_time.weekday()  # 0=Monday, 6=Sunday
        
        # Query rules
        query = PricingRule.query.filter_by(is_active=True)
        
        # Lọc theo user (nếu có custom pricing cho user)
        if user_id:
            user_rules = query.filter(
                (PricingRule.user_id == user_id) | (PricingRule.user_id.is_(None))
            )
        else:
            user_rules = query.filter(PricingRule.user_id.is_(None))
        
        applicable_rules = []
        
        for rule in user_rules.all():
            # Kiểm tra time-based rules
            if rule.rule_type == "time_based":
                if rule.start_hour is not None and rule.end_hour is not None:
                    # Xử lý qua đêm (ví dụ: 22h - 6h)
                    if rule.start_hour > rule.end_hour:
                        # Qua đêm: 22h - 6h
                        if entry_hour >= rule.start_hour or entry_hour < rule.end_hour:
                            if not rule.days_of_week or str(entry_weekday) in rule.days_of_week.split(","):
                                applicable_rules.append(rule)
                    else:
                        # Trong ngày: 6h - 22h
                        if rule.start_hour <= entry_hour < rule.end_hour:
                            if not rule.days_of_week or str(entry_weekday) in rule.days_of_week.split(","):
                                applicable_rules.append(rule)
                else:
                    # Không có khung giờ, áp dụng cho tất cả
                    applicable_rules.append(rule)
            elif rule.rule_type in ("flat_rate", "per_hour", "overnight", "custom"):
                # Áp dụng cho tất cả thời gian
                applicable_rules.append(rule)
        
        # Sắp xếp theo priority (cao -> thấp)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        return applicable_rules
    
    @staticmethod
    def _apply_pricing_rule(rule: "PricingRule", session: ParkingSession) -> int:
        """Áp dụng pricing rule để tính phí."""
        duration_minutes = session.duration_minutes
        hours = (duration_minutes + 59) // 60  # Làm tròn lên
        
        if hours == 0:
            return 0
        
        if rule.rule_type == "flat_rate":
            # Đồng giá
            return rule.flat_rate_fee or 0
        
        elif rule.rule_type == "overnight":
            # Qua đêm: tính theo số đêm
            entry_time = session.entry_time
            exit_time = session.exit_time or datetime.now(UTC)
            
            # Đếm số đêm (nếu entry và exit khác ngày)
            if entry_time.date() != exit_time.date():
                nights = (exit_time.date() - entry_time.date()).days
                return (nights + 1) * (rule.overnight_fee or 0)
            else:
                # Cùng ngày, tính theo giờ
                if hours == 1:
                    return rule.first_hour_fee or 0
                else:
                    return (rule.first_hour_fee or 0) + (hours - 1) * (rule.subsequent_hour_fee or 0)
        
        elif rule.rule_type == "per_hour":
            # Theo giờ
            if hours == 1:
                return rule.first_hour_fee or 0
            else:
                return (rule.first_hour_fee or 0) + (hours - 1) * (rule.subsequent_hour_fee or 0)
        
        elif rule.rule_type == "time_based":
            # Theo khung giờ
            if hours == 1:
                return rule.first_hour_fee or 0
            else:
                return (rule.first_hour_fee or 0) + (hours - 1) * (rule.subsequent_hour_fee or 0)
        
        elif rule.rule_type == "custom":
            # Tùy chỉnh (có thể mở rộng)
            if hours == 1:
                return rule.first_hour_fee or 0
            else:
                return (rule.first_hour_fee or 0) + (hours - 1) * (rule.subsequent_hour_fee or 0)
        
        # Fallback
        return 0
    
    @staticmethod
    def mark_paid(session_id: int, payment_method: str = "cash", user_id: Optional[int] = None) -> Optional[ParkingSession]:
        """Đánh dấu session đã thanh toán."""
        session = ParkingSession.query.get(session_id)
        if not session:
            return None
        
        session.payment_status = "paid"
        session.payment_time = datetime.now(UTC)
        session.payment_method = payment_method
        
        # Log event
        db.session.add(SystemLog(
            event_type="payment_completed",
            message=f"Đã thanh toán {session.fee_amount:,} VNĐ cho session {session_id}",
            user_id=user_id,
            meta_data={
                "session_id": session_id,
                "fee_amount": session.fee_amount,
                "payment_method": payment_method,
            },
        ))
        
        db.session.commit()
        return session
    
    @staticmethod
    def get_statistics() -> dict:
        """Get parking statistics."""
        total_sessions = ParkingSession.query.count()
        active_sessions = ParkingSession.query.filter_by(status="active").count()
        completed_sessions = ParkingSession.query.filter_by(status="completed").count()

        # Today's statistics
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_sessions = ParkingSession.query.filter(ParkingSession.entry_time >= today_start).count()
        
        # Revenue statistics
        total_revenue = db.session.query(db.func.sum(ParkingSession.fee_amount)).filter(
            ParkingSession.payment_status == "paid"
        ).scalar() or 0
        
        today_revenue = db.session.query(db.func.sum(ParkingSession.fee_amount)).filter(
            ParkingSession.payment_status == "paid",
            ParkingSession.payment_time >= today_start
        ).scalar() or 0

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "today_sessions": today_sessions,
            "total_revenue": total_revenue,
            "today_revenue": today_revenue,
        }

