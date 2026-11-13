# OkeyDocu - okeydocu/devices/profitest_prime/texts.py
# The instrument's translation file: one block per language, a text for each TS code.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import xml.etree.ElementTree as ET

from ...l10n import tr
from ..base import DeviceError, DeviceTexts

TEXTS_COMMAND = "DATABASEXML:GET:TRANSLATIONFILE"
TEXTS_TIMEOUT_S = 150.0  # about a minute over Bluetooth for all twelve languages


def _name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_texts(raw: bytes) -> DeviceTexts:
    """`<MoFile Culture=… Version=…>` holds `<TRANSLATION Key="TS1165">RISO</TRANSLATION>`."""
    start = raw.find(b"<")
    try:
        root = ET.fromstring(raw[start:] if start >= 0 else raw)
    except ET.ParseError as err:
        raise DeviceError(tr("The instrument texts cannot be read: {error}", error=err)) from None
    texts: dict[str, dict[str, str]] = {}
    version = ""
    for block in root.iter():
        if _name(block.tag) != "MoFile" or not block.get("Culture"):
            continue
        version = version or block.get("Version", "")
        texts[block.get("Culture")] = {
            entry.get("Key"): (entry.text or "").strip()
            for entry in block.iter() if _name(entry.tag) == "TRANSLATION" and entry.get("Key")
        }
    if not texts:
        raise DeviceError(tr("The instrument delivered no texts."))
    return DeviceTexts(version, texts)
