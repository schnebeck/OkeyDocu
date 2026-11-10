# EasyMeasurement - tests/test_driver_boundary.py
# The application knows instruments only by what their drivers say about themselves.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

import easymeasurement
from easymeasurement.campaign.plan import parse_plan, says_draft
from easymeasurement.devices import available_drivers, driver_info, is_simulated
from easymeasurement.l10n import qt_moment, speaking

PACKAGE = Path(easymeasurement.__file__).parent
DRIVER_IMPORT = re.compile(r"devices\.(profitest_prime|simulator)\b|from \.(profitest_prime|simulator)")
# The UI drives the simulator itself; the IZYTRON import reads a PROFITEST PRIME's results.
KNOWS_A_DRIVER = {
    "ui/common.py",
    "ui/plan_test_run.py",
    "ui/guided.py",
    "ui/campaign_views.py",
    "importing/izytron_measurements.py",
}


def test_only_the_named_places_import_a_driver_package():
    found = set()
    for path in PACKAGE.rglob("*.py"):
        name = path.relative_to(PACKAGE).as_posix()
        if name.startswith("devices/"):
            continue
        if DRIVER_IMPORT.search(path.read_text(encoding="utf-8")):
            found.add(name)
    assert found == KNOWS_A_DRIVER


def test_drivers_describe_themselves():
    keys = {info.key for info in available_drivers()}
    assert {"profitest-prime", "simulator"} <= keys
    prime = driver_info("profitest-prime")
    assert prime.pairing is not None and prime.words is not None and prime.instructions
    assert is_simulated("simulator") and not is_simulated("profitest-prime")
    assert driver_info("manual") is None and not is_simulated("manual")


def test_a_draft_is_recognised_in_every_language():
    assert says_draft("Maschine (Entwurf)") and says_draft("Machine (draft)")
    assert not says_draft("Maschine")
    assert parse_plan("key: x\ntitle: X (draft)\nsteps: []").label == "X (draft)"


def test_moment_fields_follow_the_language():
    with speaking("de"):
        assert qt_moment() == "dd.MM.yyyy HH:mm:ss"
    with speaking("en"):
        assert qt_moment() == "yyyy-MM-dd HH:mm:ss"


def test_a_check_is_answered_by_the_underlined_letter_of_its_language(qtbot):
    from easymeasurement.ui.guided_pages import CheckPage
    with speaking("en"):
        page = CheckPage()
    qtbot.addWidget(page)
    QTest.keyClick(page, Qt.Key.Key_Y)
    assert page.buttons["yes"].isChecked()
