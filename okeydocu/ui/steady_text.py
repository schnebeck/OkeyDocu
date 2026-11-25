# OkeyDocu - okeydocu/ui/steady_text.py
# Texts of a table column that begin on one line, whether they fit their cell or not.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The style sets a text it has to cut a few pixels further left than one that fits, so a
column with long and short texts flutters. Here a text too long for its cell is cut before the
style sees it: every text fits, and all begin at the same place. The size asked for holds the
room kept free, so a column sized to its texts shows them whole."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate

SPARE = 6  # pixels kept free: a text that nearly fills its cell is set a pixel off as well


class SteadyText(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        hint = super().sizeHint(option, index)
        return QSize(hint.width() + SPARE, hint.height())

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        metrics = option.fontMetrics
        # A cell high enough for several lines wraps its text; that is left to the style.
        if option.rect.width() <= 0 or option.rect.height() >= 2 * metrics.lineSpacing():
            return
        style = option.widget.style() if option.widget is not None else QApplication.style()
        area = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, option, option.widget)
        margin = style.pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin, option,
                                   option.widget) + 1
        room = area.width() - 2 * margin - SPARE
        if room > 0 and metrics.horizontalAdvance(option.text) > room:
            option.text = metrics.elidedText(option.text, option.textElideMode, room)
