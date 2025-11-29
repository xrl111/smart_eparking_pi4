"""Wrapper đơn giản để cập nhật LCD 1602 I2C."""

from __future__ import annotations

import logging
from typing import Optional

from config import LCDConfig

try:
    from RPLCD.i2c import CharLCD  # type: ignore
except ImportError:  # pragma: no cover
    CharLCD = None

logger = logging.getLogger(__name__)


class LCDDisplay:
    """Đóng gói thao tác cập nhật LCD."""

    def __init__(
        self,
        i2c_address: int = LCDConfig.I2C_ADDRESS,
        cols: int = LCDConfig.COLS,
        rows: int = LCDConfig.ROWS,
    ) -> None:
        self._lcd: Optional[CharLCD] = None
        if CharLCD is None:
            logger.warning("Thư viện RPLCD chưa sẵn có, LCD sẽ bị bỏ qua.")
            return
        self._lcd = CharLCD(
            i2c_expander="PCF8574",
            address=i2c_address,
            cols=cols,
            rows=rows,
        )
        logger.info("Khởi tạo LCD ở địa chỉ 0x%X", i2c_address)

    def show(self, line1: str, line2: str = "") -> None:
        if not self._lcd:
            logger.debug("LCD chưa sẵn sàng => bỏ qua thông điệp: %s | %s", line1, line2)
            return
        self._lcd.clear()
        self._lcd.write_string(line1[: LCDConfig.COLS].ljust(LCDConfig.COLS))
        if LCDConfig.ROWS > 1:
            self._lcd.crlf()
            self._lcd.write_string(line2[: LCDConfig.COLS].ljust(LCDConfig.COLS))

