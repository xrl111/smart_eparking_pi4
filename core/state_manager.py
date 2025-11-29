"""Quản lý trạng thái bãi đỗ xe và cung cấp snapshot thread-safe."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Dict, List, Optional

from config import OperationMode, ParkingConfig

logger = logging.getLogger(__name__)


@dataclass
class ParkingState:
    slots: List[int] = field(default_factory=lambda: [0] * ParkingConfig.TOTAL_SLOTS)
    gate: str = "closed"
    free: int = ParkingConfig.TOTAL_SLOTS
    total_slots: int = ParkingConfig.TOTAL_SLOTS
    last_update: datetime = field(default_factory=lambda: datetime.now(UTC))
    errors: List[str] = field(default_factory=list)
    operation_mode: str = OperationMode.DEFAULT_MODE  # "auto" hoặc "manual"
    mode_locked_by: Optional[str] = None  # User đang lock chế độ (nếu có)
    button_pressed: bool = False  # Trạng thái button
    led_status: str = "green"  # "green", "yellow", "red", "yellow_blink", "error"

    def apply_payload(self, payload: Dict) -> None:
        logger.debug("Cập nhật state với payload: %s", payload)
        incoming_slots = payload.get("slots")
        if isinstance(incoming_slots, list) and incoming_slots:
            normalized = [1 if bool(v) else 0 for v in incoming_slots[: ParkingConfig.TOTAL_SLOTS]]
            # Nếu payload ít slot hơn, padding 0
            if len(normalized) < ParkingConfig.TOTAL_SLOTS:
                normalized += [0] * (ParkingConfig.TOTAL_SLOTS - len(normalized))
            # Chỉ cập nhật Slot 1 từ Arduino (sensor), Slot 2,3 giữ nguyên (manual)
            if self.operation_mode == OperationMode.AUTO:
                self.slots = normalized
            else:
                # MANUAL mode: chỉ cập nhật Slot 1 từ sensor, giữ Slot 2,3
                self.slots[0] = normalized[0] if len(normalized) > 0 else self.slots[0]
            self.free = ParkingConfig.TOTAL_SLOTS - sum(self.slots)

        # Cập nhật free_slots và total_slots từ payload (nếu có)
        free_slots = payload.get("free_slots")
        if isinstance(free_slots, int):
            if self.operation_mode == OperationMode.AUTO:
                self.free = free_slots
        
        total_slots = payload.get("total_slots")
        if isinstance(total_slots, int):
            self.total_slots = total_slots

        gate = payload.get("barrier") or payload.get("gate")  # Hỗ trợ cả "barrier" và "gate"
        if isinstance(gate, str):
            # Chỉ cập nhật gate từ Arduino nếu đang ở chế độ AUTO
            if self.operation_mode == OperationMode.AUTO:
                self.gate = gate

        errors = payload.get("errors")
        if isinstance(errors, list):
            self.errors = errors

        # Button status
        button_pressed = payload.get("button_pressed")
        if isinstance(button_pressed, bool):
            self.button_pressed = button_pressed

        # LED status
        led_status = payload.get("led_status")
        if isinstance(led_status, str):
            self.led_status = led_status

        # Chế độ và lock (chỉ cập nhật từ web, không từ Arduino)
        operation_mode = payload.get("operation_mode")
        if isinstance(operation_mode, str) and operation_mode in (OperationMode.AUTO, OperationMode.MANUAL):
            self.operation_mode = operation_mode

        mode_locked_by = payload.get("mode_locked_by")
        if mode_locked_by is not None:
            self.mode_locked_by = mode_locked_by

        self.last_update = datetime.now(UTC)

    def to_dict(self) -> Dict:
        return {
            "slots": self.slots,
            "free": self.free,
            "total_slots": self.total_slots,
            "gate": self.gate,
            "last_update": self.last_update.isoformat(),
            "errors": self.errors,
            "operation_mode": self.operation_mode,
            "mode_locked_by": self.mode_locked_by,
            "button_pressed": self.button_pressed,
            "led_status": self.led_status,
        }


class StateManager:
    def __init__(self) -> None:
        self._state = ParkingState()
        self._lock = threading.Lock()

    def update(self, payload: Dict) -> None:
        with self._lock:
            self._state.apply_payload(payload)

    def snapshot(self) -> Dict:
        with self._lock:
            return self._state.to_dict()

    def last_update(self) -> datetime:
        with self._lock:
            return self._state.last_update

