# EasyMeasurement - easymeasurement/ui/guided_actions.py
# What the operator does in a guided campaign: start it, confirm, measure, finish or skip a step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from ..campaign.plan import Plan
from ..campaign.service import NO_INSTRUMENT, read_instrument
from ..devices import Capability, DeviceError
from .common import run_busy, selected_id, show_error
from .guided_pages import ReasonOverlay


class GuidedActions:
    """Starts the campaign, then acts on the step chosen in the list."""

    def start_campaign(
        self, asset_id: int, plan: Plan, title: str, tester: str, driver_key: str, port: str = "",
        user_id: int | None = None,
    ) -> int | None:
        driver = self.app.devices.new_driver(driver_key, port)

        def connect():
            with driver:
                return read_instrument(driver)

        try:
            start = run_busy(self, "Verbinde mit dem Messgerät und stelle die Uhr …", connect)
        except DeviceError as err:
            show_error(self, str(err))
            return None
        campaign = self.app.service.open_with(
            asset_id, plan, title, tester, driver_key, start, user_id
        )
        self.app.devices.attach(campaign, driver, port)
        self.campaign_id = campaign
        self.reload()
        self.started.emit(campaign)
        self.changed.emit()
        return campaign

    # Actions -------------------------------------------------------------

    def confirm(self) -> None:
        row = self._step()
        if row is None:
            return
        self.app.service.confirm_setup(row["id"])
        self.status.setText("Aufbau bestätigt. Jetzt beliebig oft messen und am Gerät speichern.")
        self._fill_steps()

    def simulate(self) -> None:
        """Stands in for the operator measuring and saving on the instrument."""
        driver = self.app.devices.driver(self._campaign())
        if Capability.SIMULATED_TRIGGER not in driver.capabilities:
            return
        reading = driver.simulate_measurement(self.simulate_function.currentData())
        if self.instrument.session is None:
            text = "   ".join(f"{r.label} {r.quantity.raw}" for r in reading.results[:2])
            self.status.setText(f"Am Gerät gespeichert: {text}. Noch nicht abgerufen.")

    def fetch(self) -> bool:
        result = self.instrument.fetch(self.campaign_id)
        if result is None:
            return False
        self.status.setText(
            f"{result['added']} neu, {result['assigned']} zugeordnet, {result['open']} offen."
        )
        self._fill_steps()
        self.changed.emit()
        return True

    # Going through the points --------------------------------------------

    def previous(self) -> None:
        self.steps.setCurrentRow(self.steps.currentRow() - 1)

    def _go_on(self) -> None:
        """All marks are redrawn, then the next point in the plan comes up."""
        row = self.steps.currentRow()
        self._fill_steps()
        self.steps.setCurrentRow(min(row + 1, self.steps.count() - 1))
        self.changed.emit()

    def _next_if_ready(self) -> None:
        if self.next_button.isEnabled():
            self.next_point()

    def next_point(self) -> None:
        row = self._step()
        if row is None:
            return
        step = self.app.service.plan_step(row)
        if step.kind == "check":
            self._store_check(row)
        elif step.kind == "note" and row["status"] != "done":
            self.app.service.finish_step(row["id"])
        elif row["status"] == "active":
            self.finish()
            return
        self._go_on()

    def _store_check(self, row) -> None:
        page = self.check_page
        given = self.app.service.step_answer(row["id"])
        if (page.choice, page.comment_text) == given:
            return
        if page.choice == "skip":
            self.app.service.skip_step(row["id"], page.comment_text)
        else:
            self.app.service.answer_step(row["id"], page.choice, page.comment_text)

    def _check_chosen(self, choice: str) -> None:
        """The expected answer needs no more words, anything else is worth a comment."""
        step = self.app.service.plan_step(self._step())
        self.check_page.show_hint()
        if choice == step.expected:
            self.next_point()
            return
        self._update_actions()
        self.check_page.comment.setFocus()

    def _check_edited(self) -> None:
        self.check_page.show_hint()
        self._update_actions()

    def finish(self) -> None:
        """With a live connection every reading is here already, otherwise it is fetched."""
        row = self._step()
        campaign = self._campaign()
        pushed = self.instrument.session is not None or campaign["driver"] in NO_INSTRUMENT
        if row is None or not (pushed or self.fetch()):
            return
        count = len(self.app.service.measurements(self.campaign_id, row["id"]))
        if count == 0:
            answer = QMessageBox.question(
                self, "Keine Messung",
                "Dieser Schritt hat keine Messung. Trotzdem abschließen? Das Protokoll weist ihn"
                " dann als nicht gemessen aus.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.app.service.finish_step(row["id"])
        self._go_on()

    def skip(self, reason: str) -> None:
        row = self._step()
        if row is not None:
            self.app.service.skip_step(row["id"], reason)
            self._go_on()

    def _skip(self) -> None:
        overlay = ReasonOverlay(self)
        if overlay.exec():
            self.skip(overlay.reason.toPlainText().strip())

    def _assign_open(self) -> None:
        measurement = selected_id(self.open_table)
        row = self._step()
        if measurement is None or row is None:
            show_error(self, "Bitte eine Messung und links den Schritt wählen.")
            return
        self.app.service.assign_manually(measurement, row["id"])
        self._fill_steps()
        self.changed.emit()
