# EasyMeasurement - easymeasurement/ui/users.py
# The people doing the work: the list of them, and choosing one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ..campaign.service import full_name
from .campaign_list import CampaignDelegate
from .common import ROW_ID, AppContext
from .overlay import Overlay
from .user_form import UserForm


def _summary(user) -> str:
    parts = ["Unterschrift hinterlegt" if user["signature"] else "keine Unterschrift"]
    if not user["certificate_path"]:
        parts.append("kein Zertifikat")
    elif user["certificate_until"]:
        moment = datetime.fromisoformat(user["certificate_until"]).date()
        expired = moment < date.today()
        parts.append(f"Zertifikat {'abgelaufen' if expired else 'bis'} {moment:%d.%m.%Y}")
    else:
        parts.append("Zertifikat ungeprüft")
    return "  ·  ".join(parts)


class UsersOverlay(Overlay):
    def __init__(self, app: AppContext, parent=None):
        super().__init__("Benutzer", parent, 520)
        self.app = app
        self.ok_button.setText("Fertig")
        self.cancel_button.hide()
        self.list = QListWidget()
        self.list.setItemDelegate(CampaignDelegate(self.list))
        self.list.setMinimumHeight(220)
        self.list.currentRowChanged.connect(lambda _: self._update())
        self.list.itemDoubleClicked.connect(lambda _: self.edit())
        self.new_button = QPushButton("Neuer Benutzer …")
        self.edit_button = QPushButton("Ändern …")
        self.remove_button = QPushButton("Entfernen …")
        self.new_button.clicked.connect(self.add)
        self.edit_button.clicked.connect(self.edit)
        self.remove_button.clicked.connect(self.remove)
        buttons = QHBoxLayout()
        for button in (self.new_button, self.edit_button, self.remove_button):
            buttons.addWidget(button)
        buttons.addStretch()
        self.body.addWidget(self.list, 1)
        self.body.addLayout(buttons)
        self.refresh()

    def first_field(self) -> QWidget:
        return self.list if self.list.count() else self.new_button

    def refresh(self, select: int | None = None) -> None:
        self.list.clear()
        for user in self.app.db.users():
            item = QListWidgetItem(f"{full_name(user)}\n{_summary(user)}")
            item.setData(ROW_ID, user["id"])
            self.list.addItem(item)
            if user["id"] == select:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self._update()

    def _update(self) -> None:
        chosen = self.list.currentItem() is not None
        self.edit_button.setEnabled(chosen)
        self.remove_button.setEnabled(chosen)

    def _chosen(self):
        item = self.list.currentItem()
        return self.app.db.user(item.data(ROW_ID)) if item else None

    def add(self) -> None:
        form = UserForm(self.app, self)
        if form.exec():
            self.refresh(form.saved_id)

    def edit(self) -> None:
        user = self._chosen()
        if user is None:
            return
        form = UserForm(self.app, self, user)
        if form.exec():
            self.refresh(form.saved_id)

    def remove(self) -> None:
        user = self._chosen()
        if user is None:
            return
        answer = QMessageBox.question(
            self, "Benutzer entfernen",
            f"{full_name(user)} entfernen? Bestehende Kampagnen und Protokolle behalten den Namen.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.app.db.remove_user(user["id"])
            self.refresh()


class UserChoice(QWidget):
    """Choose who does the work, or add that person right here."""

    changed = Signal()

    def __init__(self, app: AppContext, selected: int | None = None):
        super().__init__()
        self.app = app
        self.combo = QComboBox()
        self.combo.setPlaceholderText("Noch kein Benutzer angelegt")
        self.combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        self.new_button = QPushButton("Neu …")
        self.new_button.clicked.connect(self._add)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.combo, 1)
        row.addWidget(self.new_button)
        self.fill(selected)

    def fill(self, selected: int | None) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        for user in self.app.db.users():
            self.combo.addItem(full_name(user), user["id"])
        self.combo.setCurrentIndex(max(self.combo.findData(selected), 0))
        self.combo.blockSignals(False)
        self.changed.emit()

    def current_id(self) -> int | None:
        return self.combo.currentData()

    def current_name(self) -> str:
        return self.combo.currentText()

    def _add(self) -> None:
        form = UserForm(self.app, self)
        if form.exec():
            self.fill(form.saved_id)
