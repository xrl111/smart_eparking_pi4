"""Điều phối các thành phần: serial, state, LCD, actuator."""

from __future__ import annotations

import logging
import threading
import time
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
        
        # Đồng bộ state
        self._last_lcd_update = None  # Track LCD update để tránh update không cần thiết
        self._last_arduino_ping = None  # Track last ping time
        self._sync_interval = 2.0  # Sync interval (seconds)
        
        # Khởi tạo chế độ mặc định
        self.mode_manager.set_mode(OperationMode.DEFAULT_MODE)

    def start(self) -> None:
        logger.info("Khởi động ParkingController với %s slot", ParkingConfig.TOTAL_SLOTS)
        self.serial_client.start()
        
        # Đợi một chút để serial kết nối, rồi đồng bộ toàn bộ state
        time.sleep(1.0)  # Đợi Arduino sẵn sàng
        
        # Đồng bộ ban đầu
        self._full_sync_to_arduino()
        
        # Bắt đầu heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

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
        """Đồng bộ hardware và cập nhật LCD trên Arduino."""
        free = snapshot.get("free", 0)
        total_slots = snapshot.get("total_slots", ParkingConfig.TOTAL_SLOTS)
        gate = snapshot.get("gate", "closed")
        mode = snapshot.get("operation_mode", OperationMode.AUTO)

        # Cập nhật LCD trên Arduino (chỉ khi thay đổi)
        line1 = f"Tong slot: {total_slots}"
        line2 = f"Con trong: {free}"
        lcd_content = f"{line1}|{line2}"
        
        # Chỉ update LCD khi có thay đổi
        if self._last_lcd_update != lcd_content:
            self._update_arduino_lcd(line1, line2)
            self._last_lcd_update = lcd_content

        # LCD trên Pi (nếu có)
        if self.lcd:
            self.lcd.show(line1, line2)

        # CHỈ điều khiển servo từ Arduino trong AUTO mode
        if self.servo and self.mode_manager.is_auto_mode():
            if gate == "open":
                self.servo.open()
            else:
                self.servo.close()

        # Buzzer đã được loại bỏ, thay bằng web notifications

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
        
        # Gửi command xuống Arduino để điều khiển barrier
        gate_cmd = "BARRIER:OPEN" if state == "open" else "BARRIER:CLOSE"
        success = self.serial_client.send_command(gate_cmd)
        if not success:
            logger.warning("Không thể gửi command barrier xuống Arduino")
        
        # Điều khiển servo nếu có (trong MANUAL mode)
        if self.servo and self.mode_manager.is_manual_mode():
            if state == "open":
                self.servo.open()
            else:
                self.servo.close()
        
        logger.info("Điều khiển barrier thủ công: %s (MANUAL mode)", state)
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
        
        # Cập nhật state
        self.state_manager.update({"slots": slots})
        
        # Gửi command xuống Arduino để cập nhật slot (chỉ Slot 2,3 - Slot 1 từ sensor)
        if slot_index > 0:  # Chỉ gửi cho Slot 2,3 (index 1,2)
            slot_cmd = f"SLOT:{slot_index + 1}:{1 if occupied else 0}"  # Slot 1,2,3 (không phải index)
            success = self.serial_client.send_command(slot_cmd)
            if not success:
                logger.warning("Không thể gửi command slot xuống Arduino")
        
        logger.info("Đặt slot %s thủ công: %s (MANUAL mode)", slot_index + 1, "occupied" if occupied else "free")
        return True

    def _update_arduino_lcd(self, line1: str, line2: str) -> None:
        """Cập nhật LCD trên Arduino với format mới."""
        # Format: LCD:UPDATE:line1|line2
        lcd_cmd = f"LCD:UPDATE:{line1}|{line2}"
        self.serial_client.send_command(lcd_cmd)

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
    
    def _full_sync_to_arduino(self) -> None:
        """Đồng bộ toàn bộ state xuống Arduino (khi kết nối lại hoặc khởi động)."""
        snapshot = self.state_manager.snapshot()
        
        # Đồng bộ mode
        mode = snapshot.get("operation_mode", OperationMode.DEFAULT_MODE)
        self._sync_mode_to_arduino(mode)
        
        # Đồng bộ LCD
        free = snapshot.get("free", 0)
        total_slots = snapshot.get("total_slots", ParkingConfig.TOTAL_SLOTS)
        line1 = f"Tong slot: {total_slots}"
        line2 = f"Con trong: {free}"
        self._update_arduino_lcd(line1, line2)
        self._last_lcd_update = f"{line1}|{line2}"
        
        # Đồng bộ slots (nếu ở MANUAL mode)
        if mode == OperationMode.MANUAL:
            slots = snapshot.get("slots", [])
            for idx, status in enumerate(slots):
                if idx > 0:  # Slot 2,3 (index 1,2)
                    slot_cmd = f"SLOT:{idx + 1}:{status}"
                    self.serial_client.send_command(slot_cmd)
        
        # Đồng bộ barrier (nếu ở MANUAL mode)
        if mode == OperationMode.MANUAL:
            gate = snapshot.get("gate", "closed")
            gate_cmd = "BARRIER:OPEN" if gate == "open" else "BARRIER:CLOSE"
            self.serial_client.send_command(gate_cmd)
        
        logger.info("Đã đồng bộ toàn bộ state xuống Arduino")
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat loop để kiểm tra kết nối và đồng bộ định kỳ."""
        while True:
            try:
                time.sleep(self._sync_interval)
                
                # Ping Arduino để kiểm tra kết nối
                if self.serial_client.send_command("PING"):
                    self._last_arduino_ping = time.time()
                
                # Đồng bộ LCD định kỳ (đảm bảo không bị mất đồng bộ)
                snapshot = self.state_manager.snapshot()
                free = snapshot.get("free", 0)
                total_slots = snapshot.get("total_slots", ParkingConfig.TOTAL_SLOTS)
                line1 = f"Tong slot: {total_slots}"
                line2 = f"Con trong: {free}"
                lcd_content = f"{line1}|{line2}"
                
                # Update mỗi 5 giây để đảm bảo đồng bộ
                if time.time() - (self._last_arduino_ping or 0) > 5.0:
                    self._update_arduino_lcd(line1, line2)
                    self._last_lcd_update = lcd_content
                    
            except Exception as e:
                logger.error("Lỗi trong heartbeat loop: %s", e)
                time.sleep(1.0)

