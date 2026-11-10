# EasyMeasurement - easymeasurement/store/device_texts.py
# The texts an instrument has for its codes, and settings put into words with them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Measurements keep the codes the instrument sends, as IZYTRON does; words for them are
looked up when shown, so one measurement reads in any language the instrument knows."""

from __future__ import annotations

import re
from datetime import datetime

CODE = re.compile(r"^TS\d{4}$")
GERMAN = "de-DE"
# The report's languages onto the instrument's; one it lacks falls back to English.
CULTURES = {"de": "de-DE", "en": "en-GB"}
FALLBACK = "en-GB"


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

    def device_words(self, culture: str = GERMAN) -> dict[str, str]:
        """Code to text in one of the instrument's languages, over every instrument known."""
        return {row["code"]: row["text"] for row in self.query(
            "SELECT code, text FROM device_texts WHERE language=?", culture)}

    def setting_words(self, key: str, value: str, words: dict[str, str]) -> tuple[str, str]:
        """A setting as words where they are known; a code without a text stays a code."""
        def say(text: str) -> str:
            return words.get(text, text) if CODE.match(text or "") else text
        return say(key), say(value)
