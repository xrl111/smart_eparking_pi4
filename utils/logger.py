"""Cấu hình logging tập trung cho Smart E-Parking."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config import LogConfig


def configure_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Thiết lập logging theo cấu hình."""

    target_level = getattr(logging, (level or LogConfig.LOG_LEVEL).upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(target_level)
    logger.handlers.clear()

    if LogConfig.ENABLE_CONSOLE_LOGGING:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(target_level)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(console_handler)

    if LogConfig.ENABLE_FILE_LOGGING:
        log_path = Path(log_file or LogConfig.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
        file_handler.setLevel(target_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

