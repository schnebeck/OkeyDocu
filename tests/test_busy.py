# EasyMeasurement - tests/test_busy.py
# Slow work in the background: the window waits, and the operator may stop it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import threading

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QProgressDialog, QWidget

from easymeasurement.devices import Cancelled, DeviceError
from easymeasurement.ui.common import run_busy


def _press_cancel(window):
    def press():
        dialogs = window.findChildren(QProgressDialog)
        if dialogs:
            dialogs[0].canceled.emit()
        else:
            QTimer.singleShot(20, press)
    QTimer.singleShot(50, press)


def test_cancelling_stops_the_work_and_says_nothing_more(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    stop = threading.Event()

    def work():
        if stop.wait(5):
            raise DeviceError("cut short")
        return "done"

    _press_cancel(window)
    with pytest.raises(Cancelled):
        run_busy(window, "Warten …", work, stop.set)
    assert window.isEnabled()


def test_work_done_before_the_cancel_keeps_its_result(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    assert run_busy(window, "Warten …", lambda: 42, lambda: None) == 42
