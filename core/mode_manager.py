"""Quản lý chế độ hoạt động (Auto/Manual) và xử lý xung đột."""

from __future__ import annotations

import logging
from typing import Optional

from config import OperationMode
from core.state_manager import StateManager
from database.db import db
from database.models import SystemLog, User

logger = logging.getLogger(__name__)


class ModeManager:
    """Quản lý chế độ hoạt động và xử lý xung đột."""

    def __init__(self, state_manager: StateManager) -> None:
        self.state_manager = state_manager

    def get_mode(self) -> str:
        """Lấy chế độ hiện tại."""
        snapshot = self.state_manager.snapshot()
        return snapshot.get("operation_mode", OperationMode.DEFAULT_MODE)

    def set_mode(self, mode: str, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """
        Chuyển đổi chế độ.
        
        Args:
            mode: "auto" hoặc "manual"
            user_id: ID của user thực hiện (để log)
            username: Username của user (để hiển thị)
        
        Returns:
            True nếu thành công, False nếu lỗi
        """
        if mode not in (OperationMode.AUTO, OperationMode.MANUAL):
            logger.warning("Chế độ không hợp lệ: %s", mode)
            return False

        current_mode = self.get_mode()
        if current_mode == mode:
            logger.debug("Chế độ đã là %s, không cần thay đổi", mode)
            return True

        # Cập nhật state
        self.state_manager.update({
            "operation_mode": mode,
            "mode_locked_by": username if mode == OperationMode.MANUAL else None,
        })

        # Log event
        try:
            log = SystemLog(
                event_type="mode_change",
                message=f"Chuyển sang chế độ {mode.upper()}",
                user_id=user_id,
                meta_data={"old_mode": current_mode, "new_mode": mode, "username": username},
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error("Không thể log mode change: %s", e)

        logger.info("Chế độ đã chuyển từ %s sang %s (bởi user: %s)", current_mode, mode, username)
        return True

    def is_auto_mode(self) -> bool:
        """Kiểm tra có đang ở chế độ AUTO không."""
        return self.get_mode() == OperationMode.AUTO

    def is_manual_mode(self) -> bool:
        """Kiểm tra có đang ở chế độ MANUAL không."""
        return self.get_mode() == OperationMode.MANUAL

    def can_control_from_arduino(self) -> bool:
        """Kiểm tra Arduino có thể điều khiển không (chỉ trong AUTO mode)."""
        return self.is_auto_mode()

    def can_control_from_web(self) -> bool:
        """Kiểm tra Web có thể điều khiển không (chỉ trong MANUAL mode)."""
        return self.is_manual_mode()

    def get_mode_info(self) -> dict:
        """Lấy thông tin chi tiết về chế độ hiện tại."""
        snapshot = self.state_manager.snapshot()
        mode = snapshot.get("operation_mode", OperationMode.DEFAULT_MODE)
        locked_by = snapshot.get("mode_locked_by")

        return {
            "mode": mode,
            "is_auto": mode == OperationMode.AUTO,
            "is_manual": mode == OperationMode.MANUAL,
            "locked_by": locked_by,
            "arduino_control": self.can_control_from_arduino(),
            "web_control": self.can_control_from_web(),
        }

