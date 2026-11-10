# EasyMeasurement - easymeasurement/ui/repeat_point.py
# One point of a repeat inspection beside the table: what to take, how, and what was found.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .common import AppContext
from .growing_edit import GrowingEdit
from .guided_pages import ReasonOverlay
from .overlay import Overlay
from .photo_shared import shared_thumbs
from .place_line import PlaceLine

HINT_STYLE = ("#hint { border-left: 3px solid palette(mid); padding-left: 6px; }")


def _label(wrap: bool = True, dim: bool = False) -> QLabel:
    label = QLabel()
    label.setWordWrap(wrap)
    label.setEnabled(not dim)
    return label


def _tool(theme: str, fallback: QStyle.StandardPixmap, tip: str) -> QToolButton:
    button = QToolButton()
    button.setIcon(QIcon.fromTheme(theme, button.style().standardIcon(fallback)))
    button.setAutoRaise(True)
    button.setToolTip(tip)
    return button


class HintOverlay(Overlay):
    def __init__(self, text: str, parent=None):
        super().__init__("Hinweis bearbeiten", parent)
        self.ok_button.setText("Übernehmen")
        self.text = GrowingEdit("Wie hier zu messen ist")
        self.text.setPlainText(text)
        self.body.addWidget(self.text)

    def first_field(self):
        return self.text


class RepeatPoint(QWidget):
    """What the point asks for, last time's hint ready to go on, and its photos."""

    changed = Signal()
    by_hand = Signal(object)  # the plan step to enter by hand

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.row = self.step = None
        self.title = _label()
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        self.state = _label(dim=True)
        self.place = PlaceLine(app)
        self.settings = _label()
        self.question = _label()
        self.hint_box = QFrame(objectName="hint")
        self.hint_box.setStyleSheet(HINT_STYLE)
        self.hint_from = _label(dim=True)
        self.hint = _label()
        self.remark = _label(dim=True)
        edit = _tool("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView,
                     "Hinweis bearbeiten")
        drop = _tool("edit-delete", QStyle.StandardPixmap.SP_TrashIcon,
                     "Hinweis nicht übernehmen; er erscheint dann auch künftig nicht mehr")
        edit.clicked.connect(self._edit_hint)
        drop.clicked.connect(lambda: self._set_hint(""))
        head = QHBoxLayout()
        head.addWidget(self.hint_from, 1)
        head.addWidget(edit)
        head.addWidget(drop)
        box = QVBoxLayout(self.hint_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.addLayout(head)
        box.addWidget(self.hint)
        self.photos = QListWidget()
        self.photos.setViewMode(QListWidget.ViewMode.IconMode)
        self.photos.setIconSize(QSize(96, 72))
        self.photos.setFixedHeight(96)
        self.photos.setToolTip("Fotos der letzten Messung, zur Orientierung")
        self.answer_note = QLineEdit(placeholderText="Bemerkung zur Antwort")
        self.yes_button, self.no_button = QPushButton("Ja"), QPushButton("Nein")
        self.yes_button.clicked.connect(lambda: self._answer("yes"))
        self.no_button.clicked.connect(lambda: self._answer("no"))
        self.hand_button = QPushButton("Von Hand eintragen …")
        self.hand_button.clicked.connect(lambda: self.by_hand.emit(self.step))
        self.skip_button = QPushButton("Auslassen …")
        self.skip_button.clicked.connect(self._skip)
        self.reopen_button = QPushButton("Wieder öffnen")
        self.reopen_button.clicked.connect(self._reopen)
        buttons = QHBoxLayout()
        for button in (self.yes_button, self.no_button, self.hand_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.reopen_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.title, self.state, self.place, self.question, self.settings,
                       self.hint_box, self.remark, self.photos, self.answer_note):
            layout.addWidget(widget)
        layout.addLayout(buttons)

    def show_point(self, step_id: int) -> None:
        self.row = self.app.db.one("SELECT * FROM steps WHERE id=?", step_id)
        self.step = step = self.app.service.plan_step(self.row)
        skipped = self.row["status"] == "skipped"
        check = step.kind == "check"
        self.title.setText(step.title)
        self.state.setText(f"Ausgelassen: {self.row['note']}" if skipped else
                           "Noch zu beantworten" if check else
                           "Noch zu messen: am Gerät messen und senden, solange dieser Punkt"
                           " gewählt ist, oder von Hand eintragen.")
        self.place.setVisible(step.asset_id is not None)
        if step.asset_id is not None:
            self.place.show_asset(step.asset_id, False)
        self.question.setText(step.question if check and step.question != step.title else "")
        self.question.setVisible(bool(self.question.text()))
        words = self.app.db.device_words()
        settings = ["{}: {}".format(*self.app.db.setting_words(key, value, words))
                    for key, value in step.parameters]
        settings += [f"Grenze {label}: {' '.join(p for p in (low, up) if p)}"
                     for _, label, low, up in step.limits]
        self.settings.setText("Wie zuletzt:  " + "  ·  ".join(settings) if settings else "")
        self.settings.setVisible(bool(settings))
        origin = self.app.service.origin_measurement(step)
        day = datetime.fromisoformat(origin["closed_at"]) if origin else None
        self.hint_from.setText(f"Hinweis aus der Prüfung vom {day:%d.%m.%Y}" if day else "Hinweis")
        self.hint.setText(step.hint)
        self.hint_box.setVisible(bool(step.hint))
        self.remark.setText(f"Bemerkung damals: {step.remark}" if step.remark else "")
        self.remark.setVisible(bool(step.remark))
        self._show_photos(origin)
        for widget in (self.yes_button, self.no_button, self.answer_note):
            widget.setVisible(check and not skipped)
        self.hand_button.setVisible(not check and not skipped)
        self.skip_button.setVisible(not skipped)
        self.reopen_button.setVisible(skipped)
        self.answer_note.clear()

    def _show_photos(self, origin) -> None:
        self.photos.clear()
        paths = self.app.service.photo_paths(origin["id"]) if origin else []
        for path in paths:
            pixmap = shared_thumbs().get(str(path))
            self.photos.addItem(QListWidgetItem(QIcon(pixmap) if pixmap else QIcon(), path.name))
        self.photos.setVisible(bool(paths))

    def _set_hint(self, text: str) -> None:
        self.app.service.set_point_hint(self.row["id"], text)
        self.show_point(self.row["id"])

    def _edit_hint(self) -> None:
        overlay = HintOverlay(self.step.hint, self)
        if overlay.exec():
            self._set_hint(overlay.text.toPlainText())

    def _answer(self, answer: str) -> None:
        self.app.service.answer_step(self.row["id"], answer, self.answer_note.text().strip())
        self.changed.emit()

    def _skip(self) -> None:
        overlay = ReasonOverlay(self, "Punkt auslassen")
        if overlay.exec():
            self.app.service.skip_step(self.row["id"], overlay.reason.toPlainText().strip())
            self.changed.emit()

    def _reopen(self) -> None:
        self.app.service.reopen_point(self.row["id"])
        self.changed.emit()
