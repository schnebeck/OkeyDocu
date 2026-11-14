# OkeyDocu - okeydocu/ui/template_overlays.py
# Saving a campaign as a template, renaming the copied tree, taking over what was learned.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QListWidget, \
    QListWidgetItem, QTableWidget, QTableWidgetItem

from ..campaign.templates import OPEN, SERIES
from ..l10n import N_, tr
from .overlay import Overlay

MODES = ((OPEN, N_("open: learns from every campaign")),
         (SERIES, N_("series: points fixed, deviations need a reason")))
INDENT = "    "


def mode_box(current: str = OPEN) -> QComboBox:
    box = QComboBox()
    for key, text in MODES:
        box.addItem(tr(text), key)
    box.setCurrentIndex(max(box.findData(current), 0))
    return box


class TemplateSaveOverlay(Overlay):
    def __init__(self, title: str, parent=None):
        super().__init__(tr("Save as campaign template"), parent)
        self.ok_button.setText(tr("Save"))
        self.title = QLineEdit(title)
        self.title.textChanged.connect(lambda text: self.ok_button.setEnabled(bool(text.strip())))
        self.mode = mode_box()
        form = QFormLayout()
        form.addRow(tr("Title"), self.title)
        form.addRow(tr("Mode"), self.mode)
        self.body.addLayout(form)
        about = QLabel(tr("Keeps the structure of the installation and every point measured, in"
                          " the order measured, without the values."))
        about.setWordWrap(True)
        self.body.addWidget(about)

    def first_field(self):
        return self.title


class TemplateCopyOverlay(Overlay):
    """The elements a template makes on another installation, names and identifiers editable."""

    def __init__(self, nodes: list[dict], installation: str, parent=None):
        super().__init__(tr("Elements for {installation}", installation=installation), parent,
                         width=640)
        self.ok_button.setText(tr("Make them"))
        self.nodes = nodes
        self.table = QTableWidget(len(nodes), 2)
        self.table.setHorizontalHeaderLabels([tr("Name"), tr("Identifier")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        for row, node in enumerate(nodes):
            self.table.setItem(row, 0, QTableWidgetItem(INDENT * (node["depth"] - 1)
                                                        + node["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(node.get("identifier") or ""))
        self.table.resizeColumnToContents(0)
        self.table.setMinimumHeight(min(360, 40 + 30 * len(nodes)))
        self.body.addWidget(QLabel(tr("The template's tree is made below this installation.")))
        self.body.addWidget(self.table)

    def names(self) -> dict[str, tuple[str, str]]:
        found = {}
        for row, node in enumerate(self.nodes):
            name = self.table.item(row, 0).text().strip() or node["name"]
            found[node["key"]] = (name, self.table.item(row, 1).text().strip())
        return found


class TemplateLearnOverlay(Overlay):
    """What the campaign did differently; each line is taken into the template on its own."""

    def __init__(self, changes: list, template: str, parent=None):
        super().__init__(tr("Improve the template “{title}”", title=template), parent, width=600)
        self.ok_button.setText(tr("Take over"))
        self.cancel_button.setText(tr("Not now"))
        self.changes = changes
        self.list = QListWidget()
        for change in changes:
            item = QListWidgetItem(change.label())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)
        self.list.setMinimumHeight(min(320, 40 + 26 * len(changes)))
        self.body.addWidget(QLabel(tr("This campaign went differently from its template:")))
        self.body.addWidget(self.list)

    def chosen(self) -> list:
        return [change for row, change in enumerate(self.changes)
                if self.list.item(row).checkState() == Qt.CheckState.Checked]
