# OkeyDocu - okeydocu/store/device_texts.py
# The texts an instrument has for its codes, and settings put into words with them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The texts an instrument hands out for its codes, kept per driver and language. Only the
driver's mapping knows which texts are codes; see devices/naming.py."""

from __future__ import annotations

from datetime import datetime


class DeviceTextsMixin:
    def device_text_firmware(self, driver: str) -> str | None:
        """The firmware the stored texts were read from; None before the first reading."""
        row = self.one("SELECT firmware FROM device_text_sets WHERE driver=?", driver)
        return row["firmware"] if row else None

    def save_device_texts(self, driver: str, firmware: str, version: str,
                          texts: dict[str, dict[str, str]]) -> None:
        """Replaces what was kept for this driver, so no text of older firmware lingers."""
        with self.transaction() as connection:
            connection.execute("DELETE FROM device_texts WHERE driver=?", (driver,))
            connection.executemany(
                "INSERT INTO device_texts (driver, language, code, text) VALUES (?, ?, ?, ?)",
                [(driver, language, code, text) for language, table in texts.items()
                 for code, text in table.items()])
            connection.execute(
                "INSERT INTO device_text_sets (driver, firmware, version, read_at)"
                " VALUES (?, ?, ?, ?) ON CONFLICT(driver) DO UPDATE SET firmware=excluded.firmware,"
                " version=excluded.version, read_at=excluded.read_at",
                (driver, firmware, version, datetime.now().isoformat(timespec="seconds")))

    def device_texts(self, driver: str, culture: str) -> dict[str, str]:
        """Code to text in one of the instrument's languages."""
        return {row["code"]: row["text"] for row in self.query(
            "SELECT code, text FROM device_texts WHERE driver=? AND language=?", driver, culture)}
