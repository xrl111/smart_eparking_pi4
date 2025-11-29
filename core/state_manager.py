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
    last_update: datetime = field(default_factory=lambda: datetime.now(UTC))
    errors: List[str] = field(default_factory=list)
    operation_mode: str = OperationMode.DEFAULT_MODE  # "auto" hoặc "manual"
    mode_locked_by: Optional[str] = None  # User đang lock chế độ (nếu có)

    def apply_payload(self, payload: Dict) -> None:
        logger.debug("Cập nhật state với payload: %s", payload)
        incoming_slots = payload.get("slots")
        if isinstance(incoming_slots, list) and incoming_slots:
            normalized = [1 if bool(v) else 0 for v in incoming_slots[: ParkingConfig.TOTAL_SLOTS]]
            # Nếu payload ít slot hơn, padding 0
            if len(normalized) < ParkingConfig.TOTAL_SLOTS:
                normalized += [0] * (ParkingConfig.TOTAL_SLOTS - len(normalized))
            self.slots = normalized
            self.free = ParkingConfig.TOTAL_SLOTS - sum(self.slots)

        gate = payload.get("gate")
        if isinstance(gate, str):
            # Chỉ cập nhật gate từ Arduino nếu đang ở chế độ AUTO
            if self.operation_mode == OperationMode.AUTO:
                self.gate = gate

        errors = payload.get("errors")
        if isinstance(errors, list):
            self.errors = errors

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
            "gate": self.gate,
            "last_update": self.last_update.isoformat(),
            "errors": self.errors,
            "operation_mode": self.operation_mode,
            "mode_locked_by": self.mode_locked_by,
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

