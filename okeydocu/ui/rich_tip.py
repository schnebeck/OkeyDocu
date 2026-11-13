# OkeyDocu - okeydocu/ui/rich_tip.py
# A tooltip that also shows pictures: a heading, facts, a few paragraphs and drawings.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Any widget can show one: `install_tip(widget, provider)` asks the provider for a `Tip` at
the spot the mouse rests on, so one widget, such as the list of a combo box, can tell
something different for each of its rows. The tip opens where Qt would open its own and
closes when the mouse leaves the widget, on a click or a key, or after a while."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, QTextDocument
from PySide6.QtWidgets import QFrame, QLabel, QToolTip, QVBoxLayout, QWidget
from shiboken6 import isValid

SHOWN_MS = 30_000  # long enough to read a few paragraphs and a drawing
TEXT_CHARS = 70  # widest line of text, in average characters
GRID_SHARE = 0.9  # a tip with a table may take this share of the screen's width


@dataclass(frozen=True)
class Tip:
    title: str
    rows: tuple[tuple[str, str], ...] = ()  # (name, text), shown as a two-column table
    text: str = ""  # paragraphs, separated by empty lines
    pictures: tuple[QPixmap, ...] = ()
    lines: tuple[str, ...] = ()  # a list below the pictures, such as suited methods
    lines_title: str = ""
    grid: tuple[tuple[str, ...], ...] = ()  # a table below the text, its first row the heads
    marked: int = -1  # the row of the grid, below its heads, shown in bold
    hint: str = ""  # a small line at the end, such as a key that tells more

    def html(self) -> str:
        cells = "".join(f"<tr><td style='padding-right:10px'>{escape(name)}:</td>"
                        f"<td>{escape(text)}</td></tr>" for name, text in self.rows)
        parts = [f"<b>{escape(self.title)}</b>"]
        if cells:
            parts.append(f"<table cellspacing='2'>{cells}</table>")
        parts += [f"<p>{escape(paragraph)}</p>" for paragraph in self.text.split("\n\n")
                  if paragraph.strip()]
        if self.grid:
            parts.append(self._grid_html())
        return "".join(parts)

    def _grid_html(self) -> str:
        heads, *body = self.grid
        rows = ["".join(f"<th align='left' style='padding-right:12px'>{escape(head)}</th>"
                        for head in heads)]
        for index, row in enumerate(body):
            weight = "bold" if index == self.marked else "normal"
            rows.append("".join(f"<td style='padding-right:12px; font-weight:{weight}'>"
                                f"{escape(cell)}</td>" for cell in row))
        return "<table cellspacing='2'>" + "".join(f"<tr>{row}</tr>" for row in rows) + "</table>"


Provider = Callable[[QPoint], "Tip | None"]


class TipWindow(QFrame):
    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip)
        self.setPalette(QToolTip.palette())
        self.setAutoFillBackground(True)
        self.setFrameShape(QFrame.Shape.Box)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(8, 6, 8, 8)
        self.hide_timer = QTimer(self, singleShot=True, interval=SHOWN_MS)
        self.hide_timer.timeout.connect(hide_tip)

    def show_tip(self, tip: Tip, where: QPoint) -> None:
        """Every part gets a fixed size: wrapped text and pictures would otherwise share out a
        height the window does not know before it is shown."""
        texts = [tip.html()]
        if tip.lines:
            heading = f"<b>{escape(tip.lines_title)}</b><br>" if tip.lines_title else ""
            texts.append(heading + "<br>".join(f"• {escape(line)}" for line in tip.lines))
        if tip.hint:
            texts.append(f"<small>{escape(tip.hint)}</small>")
        labels = [self._label(text) for text in texts]
        sizes = [picture.deviceIndependentSize().toSize() for picture in tip.pictures]
        screen = (QGuiApplication.screenAt(where) or QGuiApplication.primaryScreen()).geometry()
        widest = self.fontMetrics().averageCharWidth() * TEXT_CHARS
        if tip.grid:
            widest = int(screen.width() * GRID_SHARE)
        width = max([min(self._natural_width(label), widest) for label in labels]
                    + [size.width() for size in sizes])
        for label in labels:
            label.setFixedSize(width, label.heightForWidth(width))
        self.layout_.addWidget(labels[0])
        for picture, size in zip(tip.pictures, sizes):
            shown = QLabel()
            shown.setPixmap(picture)
            shown.setFixedSize(size)
            self.layout_.addWidget(shown)
        for label in labels[1:]:
            self.layout_.addWidget(label)
        self.layout_.activate()
        self.adjustSize()
        x = min(where.x() + 2, screen.right() - self.width())
        y = where.y() + 20
        if y + self.height() > screen.bottom():
            y = max(screen.top(), where.y() - self.height() - 4)
        self.move(max(screen.left(), x), y)
        self.show()
        self.hide_timer.start()

    @staticmethod
    def _natural_width(label: QLabel) -> int:
        """As wide as the text runs without wrapping; a wrapping label offers less."""
        document = QTextDocument()
        document.setDefaultFont(label.font())
        document.setDocumentMargin(0)
        document.setHtml(label.text())
        return int(document.idealWidth()) + 1

    @staticmethod
    def _label(html: str) -> QLabel:
        label = QLabel(html)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        return label


_window: TipWindow | None = None


def show_tip(tip: Tip, where: QPoint) -> TipWindow:
    """Each tip gets a window of its own, sized to its content; the one before goes."""
    global _window
    hide_tip()
    _window = TipWindow()
    _window.show_tip(tip, where)
    return _window


def hide_tip() -> None:
    """The window is let go before it hides: hiding moves the mouse over other widgets, whose
    filters call here again. Qt may have deleted it already while the application ends."""
    global _window
    window, _window = _window, None
    if window is not None and isValid(window):
        window.hide()
        window.deleteLater()


class _TipFilter(QObject):
    def __init__(self, widget: QWidget, provider: Provider):
        super().__init__(widget)
        self.provider = provider

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt's name
        kind = event.type()
        if kind == QEvent.Type.ToolTip:
            tip = self.provider(event.pos())
            if tip is None:
                hide_tip()
                return False
            show_tip(tip, event.globalPos())
            return True
        if kind in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress,
                    QEvent.Type.Hide, QEvent.Type.Wheel):
            hide_tip()
        return False


def install_tip(widget: QWidget, provider: Provider) -> None:
    """The provider answers None where there is nothing to tell; Qt's own tooltip of the widget
    then shows, if it has one."""
    widget.installEventFilter(_TipFilter(widget, provider))


def showing() -> bool:
    return _window is not None and isValid(_window) and _window.isVisible()


def widget_tip(tip: Tip, widget: QWidget) -> TipWindow:
    """Shows a tip below a widget at once, as a key such as F1 asks for it."""
    return show_tip(tip, widget.mapToGlobal(QPoint(0, widget.height() - 16)))
