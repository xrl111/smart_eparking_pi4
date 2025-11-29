"""Điểm khởi chạy chính cho Smart E-Parking backend (Raspberry Pi)."""

from __future__ import annotations

import logging
import os
import signal
import sys
from typing import Optional

from config import WebConfig
from core.controller import ParkingController
from core.state_manager import StateManager
from hardware.display.lcd import LCDDisplay
from utils.logger import configure_logging
from utils.serial_client import SerialJSONClient
from web.app import create_app

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def _build_lcd() -> Optional[LCDDisplay]:
    try:
        return LCDDisplay()
    except Exception as exc:  # pragma: no cover
        logging.warning("Không thể khởi tạo LCD: %s", exc)
        return None


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def bootstrap_controller() -> ParkingController:
    state_manager = StateManager()
    serial_port = os.getenv("SERIAL_PORT")
    simulate = _to_bool(os.getenv("SERIAL_SIMULATION"), default=not bool(serial_port))
    serial_client = SerialJSONClient(port=serial_port, simulate=simulate)
    controller = ParkingController(
        serial_client=serial_client,
        state_manager=state_manager,
        lcd=_build_lcd(),
        servo=None,  # servo điều khiển trên Arduino trong kiến trúc hiện tại
        buzzer=None,
    )
    return controller


def main() -> int:
    if load_dotenv:
        load_dotenv()
    configure_logging(level=os.getenv("LOG_LEVEL"))
    controller = bootstrap_controller()
    controller.start()

    app = create_app(controller.state_manager, controller=controller)

    # Cho phép Ctrl+C dừng cả Flask + controller
    def _handle_sigint(*_: object) -> None:
        controller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    debug_flag = _to_bool(os.getenv("FLASK_DEBUG"), default=WebConfig.DEBUG)
    app.run(host=WebConfig.HOST, port=WebConfig.PORT, debug=debug_flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

