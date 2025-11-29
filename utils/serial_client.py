"""Client đọc dữ liệu JSON từ Arduino qua Serial."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from datetime import UTC, datetime
from typing import Callable, List, Optional

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - Pi môi trường thật mới có
    serial = None

logger = logging.getLogger(__name__)


PayloadCallback = Callable[[dict], None]


class SerialJSONClient:
    """Đọc JSON từng dòng từ Serial và gọi callback khi có frame."""

    def __init__(
        self,
        port: Optional[str],
        baudrate: int = 115200,
        timeout: float = 1.0,
        reconnect_interval: float = 5.0,
        simulate: Optional[bool] = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval
        self.simulate = simulate if simulate is not None else (serial is None or not port)

        self._listeners: List[PayloadCallback] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._serial: Optional["serial.Serial"] = None
        self._is_connected = False
        self._last_received = None  # Track last received data time

    def add_listener(self, callback: PayloadCallback) -> None:
        self._listeners.append(callback)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        target = self._run_simulation if self.simulate else self._run_serial
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()
        logger.info(
            "SerialJSONClient bắt đầu ở chế độ %s",
            "mô phỏng" if self.simulate else f"serial ({self.port})",
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._serial:
            self._serial.close()

    def send_command(self, command: str, retry: int = 2) -> bool:
        """
        Gửi command xuống Arduino với retry mechanism.
        
        Args:
            command: Command string (ví dụ: "MODE:AUTO", "GATE:OPEN")
            retry: Số lần retry nếu thất bại
        
        Returns:
            True nếu gửi thành công, False nếu lỗi
        """
        if self.simulate:
            logger.debug("Simulation mode: Command '%s' ignored", command)
            return True

        if not self._serial or not self._serial.is_open:
            logger.warning("Serial chưa kết nối, không thể gửi command: %s", command)
            return False

        for attempt in range(retry + 1):
            try:
                cmd_bytes = (command + "\n").encode("utf-8")
                self._serial.write(cmd_bytes)
                self._serial.flush()  # Đảm bảo data được gửi ngay
                logger.debug("Đã gửi command xuống Arduino: %s (attempt %d)", command, attempt + 1)
                return True
            except Exception as exc:
                if attempt < retry:
                    logger.warning("Lỗi khi gửi command '%s' (attempt %d/%d): %s. Retrying...", 
                                 command, attempt + 1, retry + 1, exc)
                    time.sleep(0.1)
                else:
                    logger.error("Lỗi khi gửi command '%s' sau %d lần thử: %s", command, retry + 1, exc)
                    return False
        
        return False
    
    def is_connected(self) -> bool:
        """Kiểm tra xem có kết nối với Arduino không."""
        return self._is_connected and self._serial is not None and self._serial.is_open
    
    def get_last_received_time(self) -> Optional[float]:
        """Lấy thời gian nhận dữ liệu cuối cùng."""
        return self._last_received

    # ------------------------------------------------------------------
    def _run_serial(self) -> None:
        assert serial is not None, "pyserial chưa được cài đặt"
        while not self._stop_event.is_set():
            try:
                if not self._serial:
                    logger.info("Kết nối tới serial port %s", self.port)
                    self._serial = serial.Serial(
                        self.port, self.baudrate, timeout=self.timeout
                    )
                    self._is_connected = True
                    logger.info("Đã kết nối thành công tới Arduino")

                line = self._serial.readline().decode("utf-8").strip()
                if not line:
                    continue
                
                self._last_received = time.time()
                self._handle_line(line)
            except (serial.SerialException, OSError) as exc:  # pragma: no cover
                if self._is_connected:
                    logger.warning("Mất kết nối với Arduino: %s. Thử lại sau %.1fs", exc, self.reconnect_interval)
                    self._is_connected = False
                if self._serial:
                    try:
                        self._serial.close()
                    finally:
                        self._serial = None
                time.sleep(self.reconnect_interval)

    def _run_simulation(self) -> None:
        logger.warning("Kích hoạt chế độ mô phỏng serial để phát triển/trên PC.")
        slots = [0, 1, 0]
        gate = "closed"
        while not self._stop_event.is_set():
            idx = random.randint(0, len(slots) - 1)
            slots[idx] = 1 if slots[idx] == 0 else 0
            free = len(slots) - sum(slots)
            gate = "open" if free > 0 and random.random() > 0.5 else "closed"
            frame = {
                "slots": slots,
                "free": free,
                "gate": gate,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self._emit(frame)
            time.sleep(1.5)

    def _handle_line(self, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Bỏ qua dòng không phải JSON: %s", line)
            return
        self._emit(payload)

    def _emit(self, payload: dict) -> None:
        for callback in self._listeners:
            try:
                callback(payload)
            except Exception as exc:  # pragma: no cover - chỉ log
                logger.exception("Listener lỗi: %s", exc)

