# OkeyDocu - tests/test_wrapping_label.py
# A wrapping label takes the height its lines need, and none while it has no text.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from okeydocu.ui.wrapping_label import WrappingLabel


def shown(qtbot, text: str = "") -> WrappingLabel:
    label = WrappingLabel(text)
    qtbot.addWidget(label)
    label.show()
    return label


def test_a_label_without_text_takes_no_height_and_warns_nothing(qtbot):
    warnings = []
    previous = qInstallMessageHandler(
        lambda kind, _, text: warnings.append(text) if kind == QtMsgType.QtWarningMsg else None)
    try:
        label = shown(qtbot)
        label.resize(120, 20)
    finally:
        qInstallMessageHandler(previous)
    assert label.minimumHeight() == 0
    assert not [text for text in warnings if "Negative sizes" in text]


def test_a_narrow_label_grows_to_its_wrapped_lines(qtbot):
    label = shown(qtbot, "Ein Hinweis, der in schmaler Breite umbricht und Höhe braucht")
    label.resize(80, 20)
    assert label.minimumHeight() > 20
