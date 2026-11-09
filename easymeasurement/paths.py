# EasyMeasurement - easymeasurement/paths.py
# Where the application keeps its data (XDG, never the source tree).
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("EASYMEASUREMENT_DATA")
    if override:
        root = Path(override)
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        root = (Path(xdg) if xdg else Path.home() / ".local/share") / "EasyMeasurement"
    root.mkdir(parents=True, exist_ok=True)
    return root
