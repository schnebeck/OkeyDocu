# OkeyDocu - okeydocu/ui/template_editor.py
# Campaign templates outside a campaign: title, mode, the order of the points and their hints.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Changes are kept per template while the card is open; Apply stores them all, Cancel none.
Deleting a template happens at once, after asking: campaigns made with it keep their points."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QListWidget, QMessageBox, \
    QPushButton, QVBoxLayout

from ..l10n import tr
from .overlay import Overlay
from .template_overlays import mode_box


def node_path(template, key: str) -> str:
    names, seen = [], set()
    while key and key not in seen:
        seen.add(key)
        node = template.node(key)
        if node is None or node.get("parent") is None:
            break
        names.insert(0, " ".join(p for p in (node.get("identifier"), node["name"]) if p))
        key = node.get("parent")
    return " / ".join(names)


class TemplateEditor(Overlay):
    def __init__(self, app, parent=None):
        super().__init__(tr("Campaign templates"), parent, width=820)
        self.ok_button.setText(tr("Apply"))
        self.app = app
        self.kept = {template.key: template for template in app.service.templates()}
        self.current = None
        self.list = QListWidget()
        for template in self.kept.values():
            self.list.addItem(template.title)
        self.list.currentRowChanged.connect(self._chosen)
        self.title = QLineEdit()
        self.title.textEdited.connect(lambda text: self._set("title", text.strip()))
        self.mode = mode_box()
        self.mode.activated.connect(lambda _: self._set("mode", self.mode.currentData()))
        self.points = QListWidget()
        self.points.currentRowChanged.connect(self._point_chosen)
        self.hint = QLineEdit(placeholderText=tr("How to measure here"))
        self.hint.textEdited.connect(self._hint_edited)
        moves = QHBoxLayout()
        for text, slot in ((tr("▲ Earlier"), lambda: self._move(-1)),
                           (tr("▼ Later"), lambda: self._move(1)),
                           (tr("Remove point"), self._remove)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            moves.addWidget(button)
        delete = QPushButton(tr("Delete template …"))
        delete.clicked.connect(self._delete)
        moves.addStretch(1)
        moves.addWidget(delete)
        form = QFormLayout()
        form.addRow(tr("Title"), self.title)
        form.addRow(tr("Mode"), self.mode)
        form.addRow(tr("Points"), self.points)
        form.addRow(tr("Hint"), self.hint)
        right = QVBoxLayout()
        right.addLayout(form)
        right.addLayout(moves)
        row = QHBoxLayout()
        row.addWidget(self.list, 1)
        row.addLayout(right, 3)
        self.body.addLayout(row)
        self.list.setCurrentRow(0)
        if not self.kept:
            self.hint.setEnabled(False)
            self.footer.hint.setText(tr("Save a confirmed campaign as a template first."))

    def _chosen(self, row: int) -> None:
        self.current = list(self.kept.values())[row] if row >= 0 else None
        if self.current is None:
            return
        self.title.setText(self.current.title)
        self.mode.setCurrentIndex(max(self.mode.findData(self.current.mode), 0))
        self._fill_points(0)

    def _fill_points(self, select: int) -> None:
        self.points.blockSignals(True)
        self.points.clear()
        for point in self.current.points:
            where = node_path(self.current, point["node"])
            self.points.addItem(f"{point['title']}   ·   {where}" if where else point["title"])
        self.points.blockSignals(False)
        self.points.setCurrentRow(min(select, self.points.count() - 1))

    def _set(self, name: str, value) -> None:
        if self.current is not None:
            setattr(self.current, name, value)
            if name == "title":
                self.list.currentItem().setText(value)

    def _point_chosen(self, row: int) -> None:
        point = self.current.points[row] if self.current and row >= 0 else None
        self.hint.setText(point.get("hint", "") if point else "")

    def _hint_edited(self, text: str) -> None:
        row = self.points.currentRow()
        if self.current is not None and row >= 0:
            self.current.points[row]["hint"] = text.strip()

    def _move(self, offset: int) -> None:
        row = self.points.currentRow()
        points = self.current.points if self.current else []
        if 0 <= row < len(points) and 0 <= row + offset < len(points):
            points[row], points[row + offset] = points[row + offset], points[row]
            self._fill_points(row + offset)

    def _remove(self) -> None:
        row = self.points.currentRow()
        if self.current is not None and row >= 0:
            del self.current.points[row]
            self._fill_points(row)

    def _delete(self) -> None:
        if self.current is None:
            return
        asked = QMessageBox.question(self, tr("Delete template"),
                                     tr("Delete the campaign template “{title}”?",
                                        title=self.current.title))
        if asked == QMessageBox.StandardButton.Yes:
            self.app.service.delete_template(self.current.key)
            del self.kept[self.current.key]
            self.list.takeItem(self.list.currentRow())

    def accept(self) -> None:
        for template in self.kept.values():
            self.app.service.save_template(template)
        super().accept()
