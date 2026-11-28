# OkeyDocu - okeydocu/ui/sensor_steps.py
# What the enrolment of sensors runs beside its card, and how it marks an enrolled one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A search over several models listens with each of them at once: BlueZ serves several
searches together, and every model's search ends with the same deadline or stop."""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from ..devices import DeviceError
from ..l10n import tr

DOT = 12  # pixels of the mark of an enrolled sensor
_RUNNING: set[QThread] = set()  # steps outliving the card they were started from


class Step(QThread):
    failed = Signal(str)
    done = Signal(object)
    news = Signal(object)  # something the work tells on its way

    def __init__(self, work):
        super().__init__()
        self.work = work
        _RUNNING.add(self)
        self.finished.connect(lambda: _RUNNING.discard(self))

    def run(self) -> None:
        try:
            self.done.emit(self.work())
        except DeviceError as error:
            self.failed.emit(tr(str(error)))


def scan_all(enrolments: dict, seconds: float, heard, stopped) -> list:
    """Every sensor any of `enrolments` (key to Enrolment) hears; a model that fails is left
    out as long as another one listens."""
    found, failures = [], []

    def listen(enrolment) -> None:
        try:
            found.extend(enrolment.scan(seconds, heard, stopped))
        except DeviceError as error:
            failures.append(error)
    threads = [threading.Thread(target=listen, args=(enrolment,), daemon=True)
               for enrolment in enrolments.values()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(seconds + 30)
    if failures and len(failures) == len(threads):
        raise failures[0]
    return found


def mark(enrolled: bool) -> QIcon:
    """A green dot, or an empty place of its size so that the names stay in line."""
    picture = QPixmap(DOT, DOT)
    picture.fill(Qt.GlobalColor.transparent)
    if enrolled:
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2e9d4f"))
        painter.drawEllipse(1, 1, DOT - 2, DOT - 2)
        painter.end()
    return QIcon(picture)
