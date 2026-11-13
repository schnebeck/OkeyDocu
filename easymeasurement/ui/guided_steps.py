# EasyMeasurement - easymeasurement/ui/guided_steps.py
# The steps of a guided campaign: the list, the chosen step and what is not assigned yet.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QListWidgetItem, QTableWidgetItem

from ..devices import is_simulated
from ..l10n import tr
from . import step_text
from .common import ROW_ID, filling, function_short, value_line

STATUS_MARK = {"pending": "○", "active": "▶", "done": "✓", "skipped": "–"}
FAILED_MARK = "✗"


class GuidedSteps:
    """Keeps the step shown, its setup and the buttons in line with the stored steps."""

    # What the chosen element states for the settings it decides, and its designation.
    element: tuple = ((), "")

    # Steps ---------------------------------------------------------------

    def _fill_steps(self) -> None:
        """The point on screen stays. A campaign just opened starts at the first open one."""
        self._update_banner()
        keep = self.steps.currentRow()
        self.steps.blockSignals(True)
        self.steps.clear()
        service = self.app.service
        rows = service.steps(self.campaign_id) if self.campaign_id else []
        for row in rows:
            measured = service.measurements(self.campaign_id, row["id"])
            step = service.plan_step(row)
            mark = STATUS_MARK[row["status"]]
            if step.kind == "check" and any(m["verdict"] == "failed" for m in measured):
                mark = FAILED_MARK
            suffix = f"  ({len(measured)})" if measured and step.kind == "measure" else ""
            item = QListWidgetItem(f"{mark}  {step.title}{suffix}")
            item.setToolTip(step.title)
            item.setData(ROW_ID, row["id"])
            self.steps.addItem(item)
        self.steps.blockSignals(False)
        if rows:
            first_open = next(
                (i for i, r in enumerate(rows) if r["status"] in ("active", "pending")), 0
            )
            self.steps.setCurrentRow(keep if 0 <= keep < len(rows) else first_open)
        self._show_step()

    def show_element(self, expected: list[tuple[str, str]], element: str) -> None:
        """The settings of a measuring step follow the element readings go to."""
        self.element = (expected, element)
        row = self._step()
        step = self.app.service.plan_step(row) if row is not None else None
        if step is not None and step.kind == "measure":
            self.settings_text.setText(step_text.settings_html(step, *self.element))

    def select_step(self, step_id: int) -> None:
        for row in range(self.steps.count()):
            if self.steps.item(row).data(ROW_ID) == step_id:
                self.steps.setCurrentRow(row)
                return

    def _step(self):
        item = self.steps.currentItem()
        if item is None:
            return None
        return self.app.db.one("SELECT * FROM steps WHERE id=?", item.data(ROW_ID))

    def _show_position(self, rows: int) -> None:
        index = self.steps.currentRow()
        service = self.app.service
        steps = service.steps(self.campaign_id) if self.campaign_id else []
        done = sum(1 for row in steps if row["status"] in ("done", "skipped"))
        self.progress.setRange(0, max(rows, 1))
        self.progress.setValue(done)
        text = tr("Point {number} of {total}", number=index + 1, total=rows) if rows else ""
        if rows and done == rows:
            text += "  ·  " + tr("All points done, now rework and complete.")
        self.position.setText(text)

    def _show_step(self) -> None:
        row = self._step()
        self.device_set.setChecked(False)
        self._show_position(self.steps.count())
        if row is None:
            self.pages.setCurrentWidget(self.measure_page)
            self.wiring.show_step(None)
            for label in (self.step_title, self.settings_text, self.warnings_text,
                          self.instructions_text, self.source_text):
                label.setText("")
            self._show_open()
            self._update_actions()
            self.step_shown.emit(None)
            return
        step = self.app.service.plan_step(row)
        if step.kind == "check":
            self.pages.setCurrentWidget(self.check_page)
            self.check_page.show_step(step, *self.app.service.step_answer(row["id"]))
        elif step.kind == "note":
            self.pages.setCurrentWidget(self.note_page)
            self.note_page.show_step(step)
        else:
            self.pages.setCurrentWidget(self.measure_page)
            self._show_setup(step, row["status"])
        self._show_open()
        self._update_actions()
        self.step_shown.emit(row["id"])

    def _show_setup(self, step, status: str) -> None:
        self.wiring.show_step(
            step if step.wiring else None, connected=status == "active", locked=status != "pending"
        )
        self.step_title.setText(step_text.title_html(step))
        self.settings_text.setText(step_text.settings_html(step, *self.element))
        self.warnings_text.setText(step_text.warnings_html(step))
        self.instructions_text.setText(step_text.instructions_html(step))
        self.source_text.setText(step_text.source_html(step))
        self.simulate_function.setCurrentIndex(
            max(self.simulate_function.findData(step.function), 0)
        )
        self._read_selector()

    def _read_selector(self) -> None:
        """Asked while a step is set up. During measuring the line stays free for the pushes."""
        self.selector_hint.clear()
        row = self._step()
        session = self.instrument.session
        if session is None or session.campaign_id != self.campaign_id:
            return
        if row is not None and row["status"] != "active":
            session.read_selector()

    def show_selector(self, position) -> None:
        self.selector_hint.setText(self._selector_text(position))

    def _selector_text(self, position) -> str:
        row = self._step()
        step = self.app.service.plan_step(row) if row is not None else None
        if step is None or step.kind != "measure" or row["status"] == "active":
            return ""
        wanted = step.selector or function_short(step.function)
        if not position.label:
            return tr("⚠ The rotary switch is at no measuring position, {wanted} is needed.",
                      wanted=wanted)
        if position.rules_out(step.function):
            return tr("⚠ The rotary switch is set to {position}, {wanted} is needed.",
                      position=position.label, wanted=wanted)
        mark = "✓ " if position.functions else ""
        return mark + tr("The rotary switch is set to {position}.", position=position.label)

    def _wiring_progress(self, done: int, total: int) -> None:
        if not total:
            self.wiring_hint.setText("")
        elif done == total:
            self.wiring_hint.setText(tr("All connections made."))
        else:
            self.wiring_hint.setText(tr("Make connection {number} of {total} and click it in the"
                                        " drawing.", number=done + 1, total=total))
        self._update_actions()

    def _update_actions(self) -> None:
        campaign = self._campaign()
        row = self._step()
        status = row["status"] if row else None
        measuring = status == "active"
        self.device_set.setVisible(status in ("pending", "done", "skipped"))
        self.confirm_button.setVisible(status in ("pending", "done", "skipped"))
        self.confirm_button.setText(
            tr("Confirm setup") if status == "pending" else tr("Measure step again")
        )
        ready = self.device_set.isChecked() and (
            self.wiring.complete or self.wiring.step is None
        )
        self.confirm_button.setEnabled(status != "pending" or ready)
        simulated = bool(campaign and is_simulated(campaign["driver"]))
        self.simulate_button.setVisible(simulated)
        self.simulate_function.setVisible(simulated)
        self.simulate_button.setEnabled(measuring)
        self.simulate_function.setEnabled(measuring)
        self.fetch_button.setEnabled(bool(campaign))
        self.skip_button.setEnabled(status in ("pending", "active"))
        self.back_button.setEnabled(self.steps.currentRow() > 0)
        self.next_button.setEnabled(row is not None and self._can_go_on(row, status))

    def _can_go_on(self, row, status: str) -> bool:
        kind = self.app.service.plan_step(row).kind
        if kind == "check":
            return self.check_page.ready()
        return kind == "note" or status != "pending"

    def _show_open(self) -> None:
        service = self.app.service
        loose = service.open_measurements(self.campaign_id) if self.campaign_id else []
        with filling(self.open_table):
            self.open_table.setRowCount(len(loose))
            for index, measurement in enumerate(loose):
                self._fill_row(self.open_table, index, measurement)
                self.open_table.setItem(
                    index, 3, QTableWidgetItem(service.issue_text(measurement))
                )
        self.assign_button.setEnabled(bool(loose))
        self.loose_counted.emit(len(loose))

    def _fill_row(self, table, index: int, measurement) -> None:
        moment = datetime.fromisoformat(measurement["local_time"]).strftime("%H:%M:%S")
        text = value_line(self.app.service, measurement)
        for column, cell in enumerate((moment, function_short(measurement["function"]), text)):
            table.setItem(index, column, QTableWidgetItem(cell))
        table.item(index, 0).setData(ROW_ID, measurement["id"])
