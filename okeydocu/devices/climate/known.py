# OkeyDocu - okeydocu/devices/climate/known.py
# The climate sensors registered with this program, kept in the local data folder.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A sensor is registered once: its address, the name it calls itself, the protocol it
spoke and what it told of itself when registered, so it can be booked without a
connection. The list lives in a JSON file of the user's data folder, never with the
program, since an address belongs to one person's equipment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ...paths import data_dir

FILE = "climate-sensors.json"


@dataclass(frozen=True)
class KnownSensor:
    address: str
    name: str
    protocol: str
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""


def _path(folder: Path | None) -> Path:
    return (folder or data_dir()) / FILE


def known_sensors(folder: Path | None = None) -> list[KnownSensor]:
    path = _path(folder)
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        return [KnownSensor(**entry) for entry in entries]
    except (ValueError, TypeError):
        return []


def remember(sensor: KnownSensor, folder: Path | None = None) -> None:
    """Adds a sensor, or replaces the entry with its address."""
    entries = [known for known in known_sensors(folder) if known.address != sensor.address]
    entries.append(sensor)
    _path(folder).write_text(json.dumps([asdict(entry) for entry in entries], indent=1,
                                        ensure_ascii=False), encoding="utf-8")


def forget(address: str, folder: Path | None = None) -> None:
    entries = [known for known in known_sensors(folder) if known.address != address]
    _path(folder).write_text(json.dumps([asdict(entry) for entry in entries], indent=1,
                                        ensure_ascii=False), encoding="utf-8")
