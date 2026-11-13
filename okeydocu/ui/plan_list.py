# OkeyDocu - okeydocu/ui/plan_list.py
# The plans of a campaign in the side panel: how far each is, run one, remove one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan_blocks import PlanBlock
from ..l10n import plural, tr

BLOCK = Qt.ItemDataRole.UserRole + 1


def progress_text(block: PlanBlock) -> str:
    if block.finished:
        return tr("done")
    return tr("{done} of {total} done", done=block.done, total=block.total)


class PlanList(QWidget):
    """A double click runs the plan, as the button does."""

    run_requested = Signal(object)  # PlanBlock
    remove_requested = Signal(object)
    assign_requested = Signal()

    def __init__(self):
        super().__init__()
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(lambda _: self._run())
        self.list.currentRowChanged.connect(lambda _: self._update())
        self.run_button = QPushButton(tr("Run"))
        self.run_button.clicked.connect(self._run)
        self.remove_button = QPushButton(tr("Remove …"))
        self.remove_button.clicked.connect(
            lambda: self.chosen() and self.remove_requested.emit(self.chosen()))
        self.assign_button = QPushButton(tr("Assign test plan …"))
        self.assign_button.clicked.connect(self.assign_requested)
        row = QHBoxLayout()
        row.addWidget(self.run_button)
        row.addWidget(self.remove_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list, 1)
        layout.addLayout(row)
        layout.addWidget(self.assign_button)
        self.editable = False
        self.running: PlanBlock | None = None

    def show_blocks(self, blocks: list[PlanBlock], editable: bool,
                    running: PlanBlock | None) -> None:
        keep = self.list.currentRow()
        self.editable, self.running = editable, running
        self.list.blockSignals(True)
        self.list.clear()
        for block in blocks:
            mark = "▶  " if running is not None and running.step_ids == block.step_ids else ""
            item = QListWidgetItem(f"{mark}{block.title}\n{progress_text(block)}")
            item.setData(BLOCK, block)
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.list.setCurrentRow(keep if 0 <= keep < len(blocks) else 0)
        self.assign_button.setVisible(editable)
        self._update()

    def chosen(self) -> PlanBlock | None:
        item = self.list.currentItem()
        return item.data(BLOCK) if item is not None else None

    def _run(self) -> None:
        block = self.chosen()
        if block is not None and self.editable:
            self.run_requested.emit(block)

    def _update(self) -> None:
        block = self.chosen()
        self.run_button.setText(tr("Continue") if block and block.done else tr("Run"))
        self.run_button.setEnabled(self.editable and block is not None and self.running is None)
        self.remove_button.setEnabled(self.editable and block is not None)


def ask_remove(parent, block: PlanBlock, booked: int) -> bool:
    """Cancel is the default: Enter alone must not delete anything."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Remove test plan"))
    box.setText(tr("Remove “{title}” from the campaign?", title=block.title))
    text = plural(block.total, "Its {count} step goes with it.",
                  "Its {count} steps go with it.")
    if booked:
        text += " " + plural(booked, "{count} measurement or answer booked on them is deleted.",
                             "{count} measurements and answers booked on them are deleted.")
        text += "\n\n" + tr("This cannot be undone.")
    box.setInformativeText(text)
    remove = box.addButton(tr("Remove"), QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is remove
