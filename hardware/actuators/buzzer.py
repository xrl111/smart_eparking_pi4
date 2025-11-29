"""Điều khiển buzzer cảnh báo."""

from __future__ import annotations

import logging
import time
from typing import Optional

from config import BuzzerConfig, GPIOPins

try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:  # pragma: no cover
    GPIO = None

logger = logging.getLogger(__name__)


class Buzzer:
    def __init__(self, pin: int = GPIOPins.BUZZER_PIN) -> None:
        self.pin = pin
        self._enabled = GPIO is not None
        if self._enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
        else:
            logger.warning("RPi.GPIO chưa sẵn sàng, buzzer sẽ không hoạt động.")

    def beep(self, duration: float = BuzzerConfig.BEEP_DURATION) -> None:
        self._emit(duration)

    def error(self) -> None:
        self._emit(BuzzerConfig.ERROR_BEEP_DURATION)

    def _emit(self, duration: float) -> None:
        if self._enabled:
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(self.pin, GPIO.LOW)
        else:
            logger.debug("Giả lập buzzer trong %.2fs", duration)

