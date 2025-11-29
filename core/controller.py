"""Điều phối các thành phần: serial, state, LCD, actuator."""

from __future__ import annotations

import logging
from typing import Optional

from config import OperationMode, ParkingConfig
from hardware.actuators.buzzer import Buzzer
from hardware.actuators.servo import ServoBarrier
from hardware.display.lcd import LCDDisplay
from utils.serial_client import SerialJSONClient

from .mode_manager import ModeManager
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class ParkingController:
    def __init__(
        self,
        serial_client: SerialJSONClient,
        state_manager: Optional[StateManager] = None,
        lcd: Optional[LCDDisplay] = None,
        servo: Optional[ServoBarrier] = None,
        buzzer: Optional[Buzzer] = None,
    ) -> None:
        self.state_manager = state_manager or StateManager()
        self.mode_manager = ModeManager(self.state_manager)
        self.serial_client = serial_client
        self.lcd = lcd
        self.servo = servo
        self.buzzer = buzzer

        self.serial_client.add_listener(self._handle_payload)
        
        # Khởi tạo chế độ mặc định
        self.mode_manager.set_mode(OperationMode.DEFAULT_MODE)

    def start(self) -> None:
        logger.info("Khởi động ParkingController với %s slot", ParkingConfig.TOTAL_SLOTS)
        self.serial_client.start()
        
        # Đợi một chút để serial kết nối, rồi gửi chế độ mặc định xuống Arduino
        import time
        time.sleep(1.0)  # Đợi Arduino sẵn sàng
        self._sync_mode_to_arduino(OperationMode.DEFAULT_MODE)

    def stop(self) -> None:
        logger.info("Dừng ParkingController")
        self.serial_client.stop()
        if self.servo:
            self.servo.cleanup()

    # --------------------------------------------------------------
    def _handle_payload(self, payload: dict) -> None:
        # Get previous state
        prev_snapshot = self.state_manager.snapshot()
        prev_slots = prev_snapshot.get("slots", [])
        
        # Update state
        self.state_manager.update(payload)
        snapshot = self.state_manager.snapshot()
        current_slots = snapshot.get("slots", [])
        
        logger.debug("Snapshot mới: %s", snapshot)
        
        # Auto-create/end parking sessions based on slot changes
        self._handle_slot_changes(prev_slots, current_slots)
        
        self._sync_hardware(snapshot)

    def _sync_hardware(self, snapshot: dict) -> None:
        """Đồng bộ hardware - chỉ trong AUTO mode."""
        # CHỈ điều khiển hardware từ Arduino khi ở AUTO mode
        if not self.mode_manager.can_control_from_arduino():
            logger.debug("Đang ở MANUAL mode, bỏ qua điều khiển từ Arduino")
            return

        free = snapshot["free"]
        gate = snapshot["gate"]
        mode = snapshot.get("operation_mode", OperationMode.AUTO)

        if self.lcd:
            line1 = f"Free: {free}/{ParkingConfig.TOTAL_SLOTS}"
            line2 = f"Gate: {gate} [{mode.upper()}]"
            self.lcd.show(line1, line2)

        # CHỈ điều khiển servo từ Arduino trong AUTO mode
        if self.servo and self.mode_manager.is_auto_mode():
            if gate == "open":
                self.servo.open()
            else:
                self.servo.close()

        if self.buzzer and free == 0:
            self.buzzer.beep()

    # --------------------------------------------------------------
    # MANUAL CONTROL METHODS
    # --------------------------------------------------------------
    def manual_set_gate(self, state: str) -> bool:
        """Điều khiển gate thủ công: 'open' hoặc 'closed' (chỉ trong MANUAL mode)."""
        if state not in ("open", "closed"):
            logger.warning("Trạng thái gate không hợp lệ: %s", state)
            return False

        # Kiểm tra chế độ
        if not self.mode_manager.can_control_from_web():
            logger.warning("Không thể điều khiển gate: đang ở AUTO mode. Chuyển sang MANUAL mode trước.")
            return False
        
        # Cập nhật state manager
        self.state_manager.update({"gate": state})
        
        # Gửi command xuống Arduino để điều khiển barrier (trong MANUAL mode)
        if self.mode_manager.is_manual_mode():
            gate_cmd = "GATE:OPEN" if state == "open" else "GATE:CLOSED"
            success = self.serial_client.send_command(gate_cmd)
            if not success:
                logger.warning("Không thể gửi command gate xuống Arduino")
        
        # Điều khiển servo nếu có (trong MANUAL mode)
        if self.servo and self.mode_manager.is_manual_mode():
            if state == "open":
                self.servo.open()
            else:
                self.servo.close()
        
        logger.info("Điều khiển gate thủ công: %s (MANUAL mode)", state)
        return True

    def manual_set_slot(self, slot_index: int, occupied: bool) -> bool:
        """Đặt trạng thái slot thủ công (chỉ trong MANUAL mode)."""
        if slot_index < 0 or slot_index >= ParkingConfig.TOTAL_SLOTS:
            logger.warning("Slot index không hợp lệ: %s", slot_index)
            return False

        # Kiểm tra chế độ
        if not self.mode_manager.can_control_from_web():
            logger.warning("Không thể điều khiển slot: đang ở AUTO mode. Chuyển sang MANUAL mode trước.")
            return False
        
        snapshot = self.state_manager.snapshot()
        slots = snapshot["slots"].copy()
        slots[slot_index] = 1 if occupied else 0
        
        self.state_manager.update({"slots": slots})
        logger.info("Đặt slot %s thủ công: %s (MANUAL mode)", slot_index, "occupied" if occupied else "free")
        return True

    def manual_trigger_buzzer(self, duration: float = 0.2) -> bool:
        """Kích hoạt buzzer thủ công"""
        if self.buzzer:
            self.buzzer.beep(duration)
            logger.info("Kích hoạt buzzer thủ công")
            return True
        return False

    def _handle_slot_changes(self, prev_slots: list, current_slots: list) -> None:
        """Tự động tạo/kết thúc parking sessions khi slot thay đổi."""
        try:
            from database.db import db
            from core.parking_service import ParkingService

            for slot_id in range(len(current_slots)):
                prev_occupied = prev_slots[slot_id] if slot_id < len(prev_slots) else 0
                curr_occupied = current_slots[slot_id] if slot_id < len(current_slots) else 0

                # Slot chuyển từ trống -> có xe (xe vào)
                if prev_occupied == 0 and curr_occupied == 1:
                    try:
                        ParkingService.start_session(slot_id=slot_id, vehicle_plate=None)
                        logger.info("Tự động tạo parking session cho slot %s", slot_id)
                    except Exception as e:
                        logger.warning("Không thể tạo session cho slot %s: %s", slot_id, e)

                # Slot chuyển từ có xe -> trống (xe ra)
                elif prev_occupied == 1 and curr_occupied == 0:
                    try:
                        session = ParkingService.end_session(slot_id=slot_id)
                        if session:
                            logger.info("Tự động kết thúc parking session cho slot %s", slot_id)
                    except Exception as e:
                        logger.warning("Không thể kết thúc session cho slot %s: %s", slot_id, e)
        except ImportError:
            # Database not available, skip
            pass
        except Exception as e:
            logger.error("Lỗi khi xử lý thay đổi slot: %s", e)

    def _sync_mode_to_arduino(self, mode: str) -> None:
        """Đồng bộ chế độ xuống Arduino."""
        if mode == OperationMode.AUTO:
            self.serial_client.send_command("MODE:AUTO")
            logger.info("Đã gửi MODE:AUTO xuống Arduino")
        elif mode == OperationMode.MANUAL:
            self.serial_client.send_command("MODE:MANUAL")
            logger.info("Đã gửi MODE:MANUAL xuống Arduino")

