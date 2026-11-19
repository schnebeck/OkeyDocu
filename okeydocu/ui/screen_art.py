# OkeyDocu - okeydocu/ui/screen_art.py
# Draws a view of an instrument's display into the display's place on the panel drawing.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The display is laid out in rows, each at the height of the softkey beside it: the header
with the function's sign first, then readings, measuring path or small lines. A column at the
right edge holds what each softkey does, a bracket where it does nothing. All sizes are in
dots, 128 across the display, so the view keeps its proportions at any zoom."""

from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QPolygonF

from ..devices.screen import Key, Line, Path, Reading, Screen

INK, PAPER = QColor("#27304a"), QColor("#c9cfb8")
GRID = 128.0  # dots across the display
COLUMN = 31.0  # width of the softkey column
ROW = 0.9  # of the distance between two softkeys, the height a row takes
PLACEHOLDER = re.compile(r"\{(\w+)\}")
CENTER, LEFT, RIGHT = (Qt.AlignmentFlag.AlignCenter,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def paint_screen(painter: QPainter, box: QRectF, centres: list[float], screen: Screen,
                 stated=None) -> None:
    """`box` is the display on the widget, `centres` the heights of the softkeys beside it
    from the top; `stated` tells what the element measured states, by feature key."""
    dot = box.width() / GRID
    pitch = (centres[-1] - centres[0]) / max(len(centres) - 1, 1) or box.height()
    height = pitch * ROW
    painter.save()
    painter.setClipRect(box)
    for index, centre in enumerate(centres):
        top = centre - height / 2
        area = QRectF(box.left() + 2 * dot, top, (GRID - COLUMN - 4) * dot, height)
        slot = QRectF(box.right() - COLUMN * dot, top, (COLUMN - 1.5) * dot, height)
        if index == 0:
            _header(painter, area, screen.sign, dot)
        elif index <= len(screen.rows):
            _row(painter, area, screen.rows[index - 1], dot)
        _key(painter, slot, screen.keys[index] if index < len(screen.keys) else None, dot,
             stated)
    painter.restore()


def _text(painter: QPainter, rect: QRectF, text: str, size: float, bold: bool = False,
          align=CENTER, color: QColor = INK) -> None:
    """One line, made smaller where it would not fit the width."""
    font = QFont(painter.font())
    font.setBold(bold)
    font.setPixelSize(max(round(size), 1))
    wide = QFontMetricsF(font).horizontalAdvance(text)
    if wide > rect.width() > 0:
        font.setPixelSize(max(int(size * rect.width() / wide), 1))
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(rect, align | Qt.TextFlag.TextSingleLine, text)


def _frame(painter: QPainter, rect: QRectF, dot: float) -> None:
    painter.setPen(QPen(INK, max(0.7 * dot, 1.0)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect, dot, dot)


def _header(painter: QPainter, area: QRectF, sign: str, dot: float) -> None:
    """The function's sign in a frame, the battery beside it."""
    box = QRectF(area.left(), area.top() + dot, 40 * dot, area.height() - 3 * dot)
    _frame(painter, box, dot)
    _text(painter, box.adjusted(2 * dot, 0, -2 * dot, 0), sign, 10 * dot, bold=True)
    cell = QRectF(area.right() - 30 * dot, area.top() + dot, 30 * dot, area.height() / 2)
    _text(painter, cell, "BAT", 6.5 * dot, align=LEFT)
    battery = QRectF(cell.right() - 14 * dot, cell.top() + 2 * dot, 13 * dot, 6 * dot)
    _frame(painter, battery, dot)
    painter.fillRect(battery.adjusted(1.5 * dot, 1.5 * dot, -4 * dot, -1.5 * dot), INK)
    painter.setPen(QPen(INK, max(0.6 * dot, 1.0), Qt.PenStyle.DotLine))
    painter.drawLine(area.bottomLeft(), area.bottomRight())


def _row(painter: QPainter, area: QRectF, row, dot: float) -> None:
    if isinstance(row, Reading):
        _text(painter, QRectF(area.left(), area.top(), area.width() * 0.6, 9 * dot), row.label,
              8 * dot, bold=True, align=LEFT)
        unit = QRectF(area.right() - 24 * dot, area.bottom() - 15 * dot, 24 * dot, 14 * dot)
        _text(painter, unit, row.unit, 12 * dot, bold=True, align=RIGHT)
        painter.setPen(QPen(INK, 1.6 * dot, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        level = area.bottom() - 8 * dot
        for dash in range(3):
            start = unit.left() - (10 + dash * 9) * dot
            painter.drawLine(QPointF(start, level), QPointF(start + 6 * dot, level))
        painter.setPen(QPen(INK, max(0.6 * dot, 1.0), Qt.PenStyle.DotLine))
        painter.drawLine(area.bottomLeft(), area.bottomRight())
    elif isinstance(row, Path):
        box = area.adjusted(0, 3 * dot, -2 * dot, -3 * dot)
        _frame(painter, box, dot)
        _text(painter, box.adjusted(3 * dot, 0, -3 * dot, 0), row.text, 11 * dot, bold=True)
    elif isinstance(row, Line):
        _text(painter, area.adjusted(0, area.height() * 0.3, 0, 0), row.text, 7.5 * dot,
              align=RIGHT)


def _key(painter: QPainter, slot: QRectF, key: Key | None, dot: float, stated) -> None:
    if key is None:
        edge = slot.right() - dot
        painter.setPen(QPen(INK, max(0.8 * dot, 1.0)))
        painter.drawPolyline(QPolygonF([QPointF(edge, slot.top() + 2 * dot),
                                        QPointF(edge - 2 * dot, slot.top() + 2 * dot),
                                        QPointF(edge - 2 * dot, slot.bottom() - 2 * dot),
                                        QPointF(edge, slot.bottom() - 2 * dot)]))
        return
    box = slot.adjusted(0, dot, 0, -dot)
    _frame(painter, box, dot)
    if key.symbol == "share":
        _share(painter, box, dot)
        return
    lines = [PLACEHOLDER.sub(lambda found: _stated(stated, found[1]), line)
             for line in key.lines]
    high = box.height() / max(len(lines), 1)
    for number, line in enumerate(lines):
        cells = line.split("|")
        wide = box.width() / len(cells)
        for place, cell in enumerate(cells):
            rect = QRectF(box.left() + place * wide, box.top() + number * high, wide, high)
            inverted = key.inverted in (cell, line)
            if inverted:
                painter.fillRect(rect.adjusted(0.6 * dot, 0.6 * dot, -0.6 * dot, -0.6 * dot),
                                 INK)
            _text(painter, rect.adjusted(1.5 * dot, 0, -1.5 * dot, 0), cell,
                  min(7.5 * dot, high * 0.85), bold=inverted,
                  color=PAPER if inverted else INK)


def _stated(stated, feature: str) -> str:
    """What the element states, without the space before its unit; "?" where it says nothing."""
    return str(stated(feature) or "" if stated else "").replace(" ", "") or "?"


def _share(painter: QPainter, box: QRectF, dot: float) -> None:
    """An arrow into a tray: the result goes out."""
    middle = box.center().y()
    painter.setPen(QPen(INK, 1.8 * dot, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
    painter.drawLine(QPointF(box.left() + 3 * dot, middle), QPointF(box.left() + 11 * dot, middle))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(INK)
    painter.drawPolygon(QPolygonF([QPointF(box.left() + 15 * dot, middle),
                                   QPointF(box.left() + 10 * dot, middle - 4 * dot),
                                   QPointF(box.left() + 10 * dot, middle + 4 * dot)]))
    tray = QRectF(box.right() - 13 * dot, middle - 6 * dot, 10 * dot, 12 * dot)
    painter.setPen(QPen(INK, 1.2 * dot))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(tray)
    painter.fillRect(QRectF(tray.left(), tray.bottom() - 4 * dot, tray.width(), 4 * dot), INK)
