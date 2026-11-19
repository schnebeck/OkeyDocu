# OkeyDocu - tests/test_prime_softkeys.py
# The guides point at the softkey whose row on the display shows the setting.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from pathlib import Path

import okeydocu.devices.profitest_prime as prime_package
from okeydocu.devices.profitest_prime.guides import GUIDES as PRIME
from okeydocu.ui.station_kinds import parts_of

VOLTAGE = PRIME["u"]
THREE_PHASE = VOLTAGE.variants[0].guide


def softkeys(guide) -> tuple[str, ...]:
    return tuple(part for part in parts_of(guide.settings) if part.startswith("soft-"))


def test_each_setting_points_at_the_softkey_in_its_row_of_the_display():
    assert softkeys(PRIME["rcd_time"]) == ("soft-1", "soft-2", "soft-3")
    assert softkeys(PRIME["rlo"]) == ("soft-2", "soft-3", "soft-4")
    assert softkeys(VOLTAGE) == ("soft-4",)
    assert softkeys(THREE_PHASE) == ("soft-1",)


def test_after_the_line_voltages_the_view_is_switched_back_before_the_path_is_chosen():
    assert softkeys(THREE_PHASE.follow) == ("soft-1", "soft-4")


def test_the_result_is_shared_with_the_lowest_softkey():
    for guide in (PRIME["rcd_time"], PRIME["rlo"], VOLTAGE, THREE_PHASE):
        assert "soft-5" in parts_of(guide.steps)


def test_every_part_a_guide_points_at_is_on_the_panel():
    svg = (Path(prime_package.__file__).parent / "panel" / "front.svg").read_text()
    on_panel = set(re.findall(r'id="([a-z0-9-]+)"', svg))
    pointed = set()
    for guide in (*PRIME.values(), THREE_PHASE, THREE_PHASE.follow):
        pointed |= set(parts_of(guide.settings) + parts_of(guide.steps))
        pointed |= {part for station in guide.flow for part in parts_of(station.actions)}
    assert pointed and pointed <= on_panel
