# EasyMeasurement - easymeasurement/ui/plan_editor_points.py
# The list of points of the plan being edited.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import uuid

from ..l10n import in_language
from .common import function_short

MARKS = {"check": "?", "measure": "≈", "note": "i"}


def new_key(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class PlanEditorPoints:
    """Adding, moving and removing points. The page saves what changed."""

    def _step_text(self, step: dict) -> str:
        function = step.get("function", "")
        known = self.instructions.get(function)
        title = in_language(step.get("title", "")) or (known.title if known
                                                        else function_short(function))
        return f"{MARKS[step.get('kind', 'measure')]}   {title}"

    def _fill_steps(self, select: int) -> None:
        steps = self.data["steps"] if self.data else []
        self.steps.blockSignals(True)
        self.steps.clear()
        self.steps.addItems([self._step_text(step) for step in steps])
        self.steps.setCurrentRow(min(select, len(steps) - 1))
        self.steps.blockSignals(False)
        self._step_chosen()

    def _step_chosen(self) -> None:
        row = self.steps.currentRow()
        steps = self.data["steps"] if self.data else []
        self.form.show_step(steps[row] if 0 <= row < len(steps) else None)
        self.up_button.setEnabled(row > 0)
        self.down_button.setEnabled(0 <= row < len(steps) - 1)
        self.remove_button.setEnabled(row >= 0)
        self.run_button.setEnabled(bool(steps))

    def _step_edited(self) -> None:
        item = self.steps.currentItem()
        if item is not None:
            item.setText(self._step_text(self.form.step))
        self._edited()

    def add_step(self, kind: str) -> None:
        if self.data is None:
            return
        step = {"key": new_key("step"), "kind": kind, "title": ""}
        if kind == "measure":
            step = {"key": step["key"], "kind": kind, "function": next(iter(self.instructions))}
        row = self.steps.currentRow() + 1
        self.data["steps"].insert(row, step)
        self._fill_steps(row)
        self._edited()
        self.form.title.setFocus()

    def move_step(self, offset: int) -> None:
        row = self.steps.currentRow()
        steps = self.data["steps"]
        steps[row], steps[row + offset] = steps[row + offset], steps[row]
        self._fill_steps(row + offset)
        self._edited()

    def remove_step(self) -> None:
        row = self.steps.currentRow()
        del self.data["steps"][row]
        self._fill_steps(row)
        self._edited()
