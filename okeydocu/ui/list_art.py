# OkeyDocu - okeydocu/ui/list_art.py
# A setting list of the instrument drawn into the panel's display.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A setting list fills the display: a counter of its pages at the top, the settings of the
softkey in a column on the left, the selected one framed, and its choices on the right, one
to a row. The softkeys move up and down, pass to the choices and take one over; the last one
does nothing. Where the element measured states the value of the setting, the choice that
says the same is framed as well: it is the one to take. All sizes are in dots, as for a view."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QPolygonF

from ..devices.screen import LIST_KEYS, Setting, SettingList
from .screen_art import COLUMN, GRID, INK, LEFT, PLACEHOLDER, _frame, _stated, _text

ROWS = 10  # choices on a page
DOTTED = Qt.PenStyle.DotLine


def said(text: str) -> str:
    """A value without what names it and without spaces: `IΔN: 30mA` and `30 mA` read alike."""
    return text.rpartition(":")[2].replace(" ", "").casefold()


def page_of(setting: Setting, stated) -> tuple[int, str]:
    """The page to show and the choice on it the element names; the first page and none
    where the element says nothing or nothing listed."""
    wanted = said(str(stated(setting.feature) or "")) if stated and setting.feature else ""
    for number, page in enumerate(setting.pages):
        match = next((choice for choice in page if wanted and said(choice) == wanted), "")
        if match:
            return number, match
    return 0, ""


def paint_list(painter: QPainter, box: QRectF, centres: list[float], listing: SettingList,
               stated=None) -> None:
    dot = box.width() / GRID
    painter.save()
    painter.setClipRect(box)
    high = (centres[-1] - centres[0]) / max(len(centres) - 1, 1) * 0.9
    for index, centre in enumerate(centres):
        slot = QRectF(box.right() - COLUMN * dot, centre - high / 2, (COLUMN - 1.5) * dot, high)
        _softkey(painter, slot, LIST_KEYS[index] if index < len(LIST_KEYS) else "", dot)
    setting = listing.settings[listing.selected]
    number, match = page_of(setting, stated)
    room = QRectF(box.left() + 2 * dot, box.top() + 2 * dot, (GRID - COLUMN - 5) * dot,
                  box.height() - 4 * dot)
    counter = QRectF(room.center().x() - 14 * dot, room.top() + 2 * dot, 34 * dot, 9 * dot)
    painter.setPen(QPen(INK, max(0.7 * dot, 1.0), DOTTED))
    painter.drawRoundedRect(counter, 2 * dot, 2 * dot)
    _text(painter, counter, f"{number + 1}/{setting.page_count()}", 7 * dot, bold=True)
    body = room.adjusted(0, 15 * dot, 0, 0)
    left = QRectF(body.left(), body.top(), body.width() * 0.47, body.height())
    right = QRectF(left.right() + 2 * dot, body.top(), body.right() - left.right() - 2 * dot,
                   body.height())
    row = body.height() / ROWS
    painter.setPen(QPen(INK, max(0.7 * dot, 1.0), DOTTED))
    painter.drawRoundedRect(left, 2 * dot, 2 * dot)
    for place, entry in enumerate(listing.settings[:ROWS]):
        cell = QRectF(left.left(), left.top() + place * row, left.width(), row)
        text = PLACEHOLDER.sub(lambda found: _stated(stated, found[1]), entry.shown)
        _entry(painter, cell, text, dot, framed=place == listing.selected)
    choices = list(setting.pages[number]) if setting.pages else []
    for place in range(ROWS):
        cell = QRectF(right.left(), right.top() + place * row, right.width(), row)
        painter.setPen(QPen(INK, max(0.6 * dot, 1.0), DOTTED))
        painter.drawRect(cell)
        typed = place == len(choices) and number == len(setting.pages or ((),)) - 1 \
            and bool(setting.typed)
        if place < len(choices):
            _entry(painter, cell, choices[place], dot, framed=choices[place] == match)
        elif typed:
            _pencil(painter, QPointF(cell.left() + 5 * dot, cell.center().y()), dot)
            _text(painter, cell.adjusted(11 * dot, 0, -2 * dot, 0), setting.typed, 6.5 * dot,
                  align=LEFT)
    painter.restore()


def _entry(painter: QPainter, cell: QRectF, text: str, dot: float, framed: bool) -> None:
    if framed:
        painter.setPen(QPen(INK, max(1.2 * dot, 1.5)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(cell.adjusted(dot, 0.6 * dot, -dot, -0.6 * dot))
    _text(painter, cell.adjusted(2.5 * dot, 0, -2.5 * dot, 0), text, 6.5 * dot, bold=framed)


def _pencil(painter: QPainter, at: QPointF, dot: float) -> None:
    """A sheet with a stroke across: this value is entered by hand."""
    painter.setPen(QPen(INK, max(0.7 * dot, 1.0)))
    painter.drawRect(QRectF(at.x() - 2.5 * dot, at.y() - 2.5 * dot, 5 * dot, 5 * dot))
    painter.drawLine(QPointF(at.x() - dot, at.y() + dot), QPointF(at.x() + 4 * dot,
                                                                 at.y() - 4 * dot))


def _softkey(painter: QPainter, slot: QRectF, sign: str, dot: float) -> None:
    centre, reach = slot.center(), min(slot.width(), slot.height()) * 0.3
    if not sign:
        edge = slot.right() - dot
        painter.setPen(QPen(INK, max(0.8 * dot, 1.0)))
        painter.drawPolyline(QPolygonF([QPointF(edge, slot.top() + 2 * dot),
                                        QPointF(edge - 2 * dot, slot.top() + 2 * dot),
                                        QPointF(edge - 2 * dot, slot.bottom() - 2 * dot),
                                        QPointF(edge, slot.bottom() - 2 * dot)]))
        return
    _frame(painter, slot.adjusted(0, dot, 0, -dot), dot)
    painter.setPen(QPen(INK, 1.8 * dot, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    if sign == "take":
        painter.drawPolyline(QPolygonF([QPointF(centre.x() - reach, centre.y()),
                                        QPointF(centre.x() - reach * 0.3, centre.y() + reach),
                                        QPointF(centre.x() + reach, centre.y() - reach)]))
        return
    # An arrow pointing up, turned to where the key moves.
    painter.save()
    painter.translate(centre)
    painter.rotate({"up": 0, "right": 90, "down": 180}[sign])
    painter.drawLine(QPointF(0, reach), QPointF(0, -reach))
    painter.drawPolyline(QPolygonF([QPointF(-reach * 0.7, -reach * 0.3), QPointF(0, -reach),
                                    QPointF(reach * 0.7, -reach * 0.3)]))
    painter.restore()
