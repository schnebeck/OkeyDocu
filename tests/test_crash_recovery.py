# EasyMeasurement - tests/test_crash_recovery.py
# A guided round with the simulator that ends in a crash goes on where it stopped.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from easymeasurement.__main__ import build_context
from easymeasurement.ui import common
from easymeasurement.ui.confirm_overlay import ConfirmOverlay
from easymeasurement.ui.main_window import MainWindow

from .crash_child import CRASHED
from .guided_helpers import run_step

REPO = Path(__file__).resolve().parent.parent


def crashed_round(data: Path) -> tuple[int, int]:
    """The campaign and its readings as the crashed process saw them last."""
    env = {**os.environ, "EASYMEASUREMENT_DATA": str(data), "QT_QPA_PLATFORM": "offscreen"}
    run = subprocess.run([sys.executable, "-m", "tests.crash_child"], cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == CRASHED, run.stderr[-2000:]
    _, campaign, _, readings = run.stdout.strip().splitlines()[-1].split()
    return int(campaign), int(readings)


@pytest.fixture
def after_crash(tmp_path, qtbot, monkeypatch):
    """The round as it stands when the program is started again on the same data."""
    data = Path(os.environ["EASYMEASUREMENT_DATA"])
    campaign, readings = crashed_round(data)
    monkeypatch.setattr(common, "SIMULATED_FAILURE_RATE", 0.0)
    app = build_context()
    window = MainWindow(app)
    window.resize(1360, 900)
    qtbot.addWidget(window)
    window.show()
    yield app, window, campaign, readings
    window.campaign.shut_down()
    app.db.close()


def test_nothing_measured_before_a_crash_is_lost_or_doubled(after_crash):
    app, _, campaign, readings = after_crash
    stored = app.service.measurements(campaign)
    assert readings == 5 and len(stored) == 5
    assert len({row["device_uid"] for row in stored}) == 5
    steps = app.service.steps(campaign)
    assert [len(app.service.measurements(campaign, s["id"])) for s in steps[:2]] == [3, 2]
    assert steps[0]["status"] == "done" and steps[1]["status"] != "done"
    assert app.service.campaign(campaign)["status"] == "open"


def test_the_round_goes_on_at_the_step_it_stopped_at_and_ends_in_a_report(after_crash,
                                                                          monkeypatch):
    app, window, campaign, _ = after_crash
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(ConfirmOverlay, "exec", lambda self: 1)
    window.campaign.refresh()
    window.campaign.enter(campaign)
    page = window.guided
    second = app.service.steps(campaign)[1]
    assert page.campaign_id == campaign and page._step()["id"] == second["id"]
    run_step(page, readings=1)
    run_step(page, readings=1)
    run_step(page, readings=2)
    page.skip("Stromkreis nicht abschaltbar")
    window.campaign.finish()
    stored = app.service.measurements(campaign)
    assert len(stored) == 9 and len({row["device_uid"] for row in stored}) == 9
    assert app.service.campaign(campaign)["status"] == "closed"
    assert len(app.archive.reports(campaign)) == 1
