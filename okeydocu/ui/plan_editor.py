# OkeyDocu - okeydocu/ui/plan_editor.py
# Creating, correcting and trying out measuring plans.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import yaml
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan import load_instructions, parse_plan
from ..l10n import in_language, tr
from .board import GutterSplitter
from .common import ROW_ID, AppContext
from .plan_editor_points import PlanEditorPoints, new_key
from .plan_step_form import PlanStepForm, kept
from .plan_test_run import PlanTestRun

SAVE_DELAY_MS = 300


class PlanEditorPage(PlanEditorPoints, QWidget):
    """Every change is saved by itself. Campaigns keep the copy they got, so nothing can break."""

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.data: dict | None = None
        self.test_runs: list[PlanTestRun] = []
        self.instructions = load_instructions()
        self._saving = QTimer(self, singleShot=True, interval=SAVE_DELAY_MS)
        self._saving.timeout.connect(self.save)

        self.plans = QListWidget()
        self.plans.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.plans.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.plans.currentRowChanged.connect(lambda _: self._plan_chosen())
        self.new_button = QPushButton(tr("New"))
        self.copy_button = QPushButton(tr("Copy"))
        self.delete_button = QPushButton(tr("Delete …"))
        self.new_button.clicked.connect(self.new_plan)
        self.copy_button.clicked.connect(self.copy_plan)
        self.delete_button.clicked.connect(self.delete_plan)
        plan_buttons = QHBoxLayout()
        for button in (self.new_button, self.copy_button, self.delete_button):
            plan_buttons.addWidget(button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.plans, 1)
        left_layout.addLayout(plan_buttons)

        self.title = QLineEdit()
        self.title.setPlaceholderText(tr("Name of the test plan"))
        self.title.textEdited.connect(self._edited)
        self.released = QCheckBox(tr("Released"))
        self.released.toggled.connect(self._edited)
        head = QHBoxLayout()
        head.addWidget(self.title, 1)
        head.addWidget(self.released)
        self.steps = QListWidget()
        self.steps.currentRowChanged.connect(lambda _: self._step_chosen())
        adders = QHBoxLayout()
        adding = ((tr("+ Check question"), "check"), (tr("+ Measurement"), "measure"),
                  (tr("+ Hint"), "note"))
        for text, kind in adding:
            button = QPushButton(text)
            button.clicked.connect(lambda _, chosen=kind: self.add_step(chosen))
            adders.addWidget(button)
        self.up_button = QPushButton("↑")
        self.down_button = QPushButton("↓")
        self.remove_button = QPushButton(tr("Remove"))
        self.up_button.clicked.connect(lambda: self.move_step(-1))
        self.down_button.clicked.connect(lambda: self.move_step(1))
        self.remove_button.clicked.connect(self.remove_step)
        for button in (self.up_button, self.down_button, self.remove_button):
            adders.addWidget(button)
        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        middle_layout.addLayout(head)
        middle_layout.addWidget(self.steps, 1)
        middle_layout.addLayout(adders)

        self.form = PlanStepForm()
        self.form.changed.connect(self._step_edited)
        self.run_button = QPushButton(tr("Test run …"))
        self.run_button.clicked.connect(self.test_run)
        self.state = QLabel()
        bottom = QHBoxLayout()
        bottom.addWidget(self.state, 1)
        bottom.addWidget(self.run_button)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.form)
        right_layout.addStretch()
        right_layout.addLayout(bottom)

        splitter = GutterSplitter(objectName="plan-editor")
        for widget in (left, middle, right):
            splitter.addWidget(widget)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([230, 440, 500])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.refresh()

    # Plans ---------------------------------------------------------------

    def refresh(self, select: str | None = None) -> None:
        keep = select or (self.data or {}).get("key")
        self.plans.blockSignals(True)
        self.plans.clear()
        for row in self.app.db.plans():
            item = QListWidgetItem(in_language(row["title"]))
            item.setData(ROW_ID, row["key"])
            self.plans.addItem(item)
            if row["key"] == keep:
                self.plans.setCurrentItem(item)
        if self.plans.currentRow() < 0 and self.plans.count():
            self.plans.setCurrentRow(0)
        self.plans.blockSignals(False)
        self._plan_chosen()

    def _plan_chosen(self) -> None:
        self.save()
        item = self.plans.currentItem()
        row = None
        if item is not None:
            row = next(r for r in self.app.db.plans() if r["key"] == item.data(ROW_ID))
        self.data = yaml.safe_load(row["body"]) if row else None
        self.title.blockSignals(True)
        self.released.blockSignals(True)
        # A shipped plan keeps its title in the source language; it is shown in this one.
        self.stored_title = self.data["title"] if self.data else ""
        self.title.setText(in_language(self.stored_title))
        self.released.setChecked(bool(self.data and self.data.get("released")))
        self.title.blockSignals(False)
        self.released.blockSignals(False)
        for widget in (self.title, self.released, self.steps, self.copy_button, self.delete_button):
            widget.setEnabled(self.data is not None)
        self.state.setText("")
        self._fill_steps(0)

    def _write(self, data: dict) -> None:
        body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        self.app.db.save_plan(data["key"], data["title"], body)

    def new_plan(self) -> None:
        self.save()
        data = {"key": new_key("plan"), "title": tr("New test plan"), "released": False,
                "steps": []}
        self._write(data)
        self.refresh(data["key"])
        self.title.setFocus()
        self.title.selectAll()

    def copy_plan(self) -> None:
        self.save()
        title = tr("{title} (copy)", title=self.data["title"])
        data = {**self.data, "key": new_key("plan"), "title": title, "released": False}
        self._write(data)
        self.refresh(data["key"])

    def delete_plan(self) -> None:
        answer = QMessageBox.question(
            self, tr("Delete test plan"),
            tr("Delete “{title}”? Campaigns keep their copy of the points.",
               title=self.data["title"]),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._saving.stop()
            self.app.db.delete_plan(self.data["key"])
            self.data = None
            self.refresh()

    # Saving --------------------------------------------------------------

    def _edited(self) -> None:
        if self.data is not None:
            typed = self.title.text().strip() or tr("Untitled")
            self.data["title"] = kept(self.stored_title, typed)
            self.data["released"] = self.released.isChecked()
            self.state.setText(tr("Saving …"))
            self._saving.start()

    def save(self) -> None:
        if self.data is not None and self._saving.isActive():
            self._saving.stop()
            self._write(self.data)
            self.state.setText(tr("Saved"))
            item = self.plans.currentItem()
            if item is not None and item.data(ROW_ID) == self.data["key"]:
                item.setText(in_language(self.data["title"]))

    def hideEvent(self, event) -> None:
        self.save()
        super().hideEvent(event)

    def test_run(self) -> None:
        """Runs on a throwaway database with a simulated instrument."""
        self.save()
        body = yaml.safe_dump(self.data, allow_unicode=True, sort_keys=False)
        run = PlanTestRun(parse_plan(body))
        self.test_runs.append(run)
        run.show()
