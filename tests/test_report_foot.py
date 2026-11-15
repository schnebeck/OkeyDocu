# OkeyDocu - tests/test_report_foot.py
# The foot of a report page: identifier, day of the inspection and page number never touch.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from reportlab.lib.pagesizes import A4

from okeydocu.reporting.pdf_parts import FOOT_EDGE, FOOT_GAP, _width, foot_layout

FONT = "Helvetica"
PAGE = "Page 12 of 12"


@pytest.mark.parametrize("left", ["Draft", "Inspection 4eaa72f9-50b4-4dfd-af2c-43b0ae89c14c",
                                  "Prüfung " + "x" * 200])
def test_the_parts_of_the_foot_keep_their_distance(left):
    middle = "Tested on 2026-11-14"
    shown, middle_x = foot_layout(left, middle, PAGE, FONT)
    assert FOOT_EDGE + _width(shown, FONT) + FOOT_GAP <= middle_x + 0.01
    assert middle_x + _width(middle, FONT) + FOOT_GAP <= A4[0] - FOOT_EDGE - _width(PAGE, FONT)


def test_a_short_foot_keeps_the_day_in_the_middle():
    shown, middle_x = foot_layout("Draft", "14.11.2026", PAGE, FONT)
    assert shown == "Draft"
    assert abs(middle_x + _width("14.11.2026", FONT) / 2 - A4[0] / 2) < 0.01


def test_a_long_identifier_stays_whole_and_the_day_moves_aside():
    left = "Inspection 4eaa72f9-50b4-4dfd-af2c-43b0ae89c14c · Hall 2"
    shown, middle_x = foot_layout(left, "Tested on 2026-11-14", PAGE, FONT)
    assert shown == left and middle_x > (A4[0] - _width("Tested on 2026-11-14", FONT)) / 2
