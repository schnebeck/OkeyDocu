# EasyMeasurement - tests/clock_helpers.py
# Shared steps of the clock tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

HOUR = 3600


def open_campaign(service, asset_id, plan, meter):
    return service.start(asset_id, plan, "Prüfung", "Prüfer", "simulator", meter)
