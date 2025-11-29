"""Điều khiển servo barrier."""

from __future__ import annotations

import logging
import time
from typing import Optional

from config import GPIOPins, ServoConfig

try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:  # pragma: no cover
    GPIO = None

logger = logging.getLogger(__name__)


class ServoBarrier:
    def __init__(
        self,
        pin: int = GPIOPins.SERVO_PIN,
        frequency: int = ServoConfig.PWM_FREQUENCY,
    ) -> None:
        self.pin = pin
        self.frequency = frequency
        self._pwm: Optional["GPIO.PWM"] = None
        self._enabled = GPIO is not None

        if self._enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, self.frequency)
            self._pwm.start(self._angle_to_duty(ServoConfig.CLOSE_ANGLE))
            logger.info("Servo barrier khởi tạo trên pin %s", pin)
        else:
            logger.warning("RPi.GPIO chưa sẵn sàng, ServoBarrier chạy ở chế độ giả lập.")

    def _angle_to_duty(self, angle: float) -> float:
        return 2.5 + (angle / 18.0)

    def _set_angle(self, angle: float) -> None:
        if self._enabled and self._pwm:
            self._pwm.ChangeDutyCycle(self._angle_to_duty(angle))
        else:
            logger.debug("Giả lập servo set angle=%s", angle)

    def open(self) -> None:
        logger.info("Mở barrier")
        self._set_angle(ServoConfig.OPEN_ANGLE)
        time.sleep(ServoConfig.OPEN_DELAY)

    def close(self) -> None:
        logger.info("Đóng barrier")
        self._set_angle(ServoConfig.CLOSE_ANGLE)
        time.sleep(ServoConfig.CLOSE_DELAY)

    def cleanup(self) -> None:
        if self._enabled:
            if self._pwm:
                self._pwm.stop()
            GPIO.cleanup(self.pin)

