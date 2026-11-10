# EasyMeasurement - easymeasurement/ui/photo_preview.py
# A photo large, with numbered marks and their texts, and its role in the report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.photo_marks import ROLES, PhotoMark
from .common import AppContext
from .growing_edit import GrowingEdit
from .overlay import Overlay
from .photo_canvas import MarkCanvas

LARGE_MARGIN_PX = 200  # the card's own heading and button row
SIDE_PX = 320  # the column for role and marks
SMALL_FOR_PRINT = 1000  # pixels along the long side; below, a photo prints coarse


def read_large(path: Path, room: QSize) -> QPixmap:
    """The picture upright and as large as `room` allows, without enlarging it."""
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return QPixmap()
    if image.width() > room.width() or image.height() > room.height():
        image = image.scaled(
            room, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
    return QPixmap.fromImage(image)


def _size_words(path: Path) -> str:
    size = QImageReader(str(path)).size()
    if not size.isValid():
        return ""
    words = f"{size.width()} × {size.height()} px"
    if max(size.width(), size.height()) < SMALL_FOR_PRINT:
        words += ", klein für das Protokoll"
    return words


class PhotoPreview(Overlay):
    """With the photo's id, marks and role can be set while its campaign is open."""

    def __init__(self, title: str, caption: str, path: Path, parent: QWidget,
                 app: AppContext | None = None, photo_id: int | None = None):
        host = parent.window()
        notes = app is not None and photo_id is not None
        side = SIDE_PX if notes else 0
        room = QSize(max(host.width() - 120 - side, 240),
                     max(host.height() - LARGE_MARGIN_PX, 180))
        super().__init__(title, parent, width=room.width() + 40 + side)
        self.app, self.photo_id = app, photo_id
        self.editable = notes and app.db.one(
            "SELECT c.status FROM photos p JOIN campaigns c ON c.id = p.campaign_id"
            " WHERE p.id=?", photo_id)["status"] == "open"
        self.canvas = MarkCanvas(read_large(path, room), self.editable)
        self.rows: dict[int, GrowingEdit] = {}
        row = QHBoxLayout()
        row.addWidget(self.canvas, 1)
        if notes:
            row.addWidget(self._side(), 0)
            self.canvas.marks = app.service.photo_marks(photo_id)
            self._fill()
        self.body.addLayout(row, 1)
        self.hint.setText("  ·  ".join(part for part in (caption, _size_words(path)) if part))
        self.ok_button.setText("Übernehmen" if self.editable else "Zurück")
        self.cancel_button.setVisible(self.editable)

    def _side(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(SIDE_PX)
        column = QVBoxLayout(side)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(QLabel("<b>Im Protokoll als</b>"))
        self.roles = QButtonGroup(side)
        choices = QHBoxLayout()
        role = self.app.service.photo_role(self.photo_id)
        for key, label in ROLES.items():
            button = QRadioButton(label)
            button.setProperty("role", key)
            button.setChecked(key == role)
            button.setEnabled(self.editable)
            self.roles.addButton(button)
            choices.addWidget(button)
        column.addLayout(choices)
        column.addSpacing(8)
        column.addWidget(QLabel("<b>Markierungen</b>"))
        self.show_all = QCheckBox("Alle zeigen, sonst nur die gewählte")
        self.show_all.setChecked(True)
        self.show_all.toggled.connect(self._show_all)
        column.addWidget(self.show_all)
        help_text = QLabel("Einen Bereich markieren: ein Rechteck über das Foto ziehen. Die"
                           " Nummer erklärt der Text daneben." if self.editable else
                           "Ein Klick auf eine Zeile zeigt ihren Bereich.")
        help_text.setWordWrap(True)
        help_text.setEnabled(False)
        column.addWidget(help_text)
        self.list = QVBoxLayout()
        self.list.setSpacing(4)
        column.addLayout(self.list)
        column.addStretch(1)
        self.canvas.drawn.connect(self._add)
        self.canvas.chosen.connect(self._choose)
        return side

    def role(self) -> str:
        checked = self.roles.checkedButton()
        return checked.property("role") if checked else ""

    def marks(self) -> list[PhotoMark]:
        for mark in self.canvas.marks:
            mark.text = self.rows[mark.number].toPlainText()
        return self.canvas.marks

    def _fill(self) -> None:
        """One line per mark: its number, its text and a bin; numbers run without gaps."""
        texts = {m.number: self.rows[m.number].toPlainText() for m in self.canvas.marks
                 if m.number in self.rows}
        while self.list.count():
            self.list.takeAt(0).widget().deleteLater()
        self.rows.clear()
        for number, mark in enumerate(self.canvas.marks, start=1):
            mark.text = texts.get(mark.number, mark.text)
            mark.number = number
            self.list.addWidget(self._row(mark))

    def _row(self, mark: PhotoMark) -> QWidget:
        line = QWidget()
        layout = QHBoxLayout(line)
        layout.setContentsMargins(0, 0, 0, 0)
        badge = QLabel(f"<b>({mark.number})</b>", alignment=Qt.AlignmentFlag.AlignTop)
        edit = GrowingEdit("Was hier zu sehen ist")
        edit.setPlainText(mark.text)
        edit.setReadOnly(not self.editable)
        edit.installEventFilter(self)
        edit.setProperty("mark", mark.number)
        self.rows[mark.number] = edit
        layout.addWidget(badge)
        layout.addWidget(edit, 1)
        if self.editable:
            drop = QToolButton()
            bin_icon = drop.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            drop.setIcon(QIcon.fromTheme("edit-delete", bin_icon))
            drop.setAutoRaise(True)
            drop.setToolTip("Markierung entfernen")
            drop.clicked.connect(lambda _=False, number=mark.number: self._remove(number))
            layout.addWidget(drop, 0, Qt.AlignmentFlag.AlignTop)
        return line

    def eventFilter(self, watched, event) -> bool:
        """A text taking the focus shows its region, the hidden reference made visible."""
        if event.type() == event.Type.FocusIn and watched.property("mark") is not None:
            self.canvas.current = watched.property("mark")
            self.canvas.update()
        return super().eventFilter(watched, event)

    def _add(self, box: QRectF) -> None:
        self.marks()
        number = len(self.canvas.marks) + 1
        self.canvas.marks.append(PhotoMark(number, box.x(), box.y(), box.width(), box.height()))
        self._fill()
        self._choose(number)

    def _remove(self, number: int) -> None:
        self.marks()
        self.canvas.marks = [m for m in self.canvas.marks if m.number != number]
        self.canvas.current = None
        self._fill()
        self.canvas.update()

    def _choose(self, number: int) -> None:
        self.canvas.current = number
        self.canvas.update()
        if number in self.rows:
            self.rows[number].setFocus()

    def _show_all(self, on: bool) -> None:
        self.canvas.show_all = on
        self.canvas.update()

    def accept(self) -> None:
        if self.editable:
            self.app.service.save_photo_notes(self.photo_id, self.role(), self.marks())
        super().accept()
