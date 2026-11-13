# OkeyDocu - tests/logo_helpers.py
# A synthetic image for the logo tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io

from PIL import Image

RED = (220, 20, 20)


def png(width=400, height=200, colour=RED, mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, (width, height), colour).save(buffer, "PNG")
    return buffer.getvalue()
