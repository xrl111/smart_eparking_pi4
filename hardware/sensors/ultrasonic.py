"""Driver đo khoảng cách cho cảm biến HC-SR04."""

from __future__ import annotations

import logging
import time
from typing import Optional

from config import SensorThresholds

try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:  # pragma: no cover - dùng mô phỏng trên PC
    GPIO = None

logger = logging.getLogger(__name__)


class UltrasonicSensor:
    def __init__(self, trig_pin: int, echo_pin: int, timeout: float = SensorThresholds.SENSOR_TIMEOUT) -> None:
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.timeout = timeout
        self._enabled = GPIO is not None

        if self._enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            logger.info("Cảm biến HC-SR04 TRIG=%s ECHO=%s sẵn sàng", trig_pin, echo_pin)
        else:
            logger.warning("RPi.GPIO chưa sẵn sàng, UltrasonicSensor chỉ dùng mô phỏng.")

    def measure_distance(self) -> Optional[float]:
        if not self._enabled:
            return None

        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, False)

        pulse_start = time.time()
        start_time = pulse_start
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
            if pulse_start - start_time > self.timeout:
                logger.warning("Timeout chờ echo HIGH")
                return None

        pulse_end = time.time()
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
            if pulse_end - pulse_start > self.timeout:
                logger.warning("Timeout chờ echo LOW")
                return None

        pulse_duration = pulse_end - pulse_start
        distance_cm = pulse_duration * 17150  # tốc độ âm thanh /2
        return round(distance_cm, 2)

    def is_occupied(self, distance_cm: Optional[float]) -> Optional[bool]:
        if distance_cm is None:
            return None
        if distance_cm <= SensorThresholds.SLOT_OCCUPIED_MAX:
            return True
        if distance_cm >= SensorThresholds.SLOT_FREE_MIN:
            return False
        return None

