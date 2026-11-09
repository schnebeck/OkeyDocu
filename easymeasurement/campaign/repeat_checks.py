# EasyMeasurement - easymeasurement/campaign/repeat_checks.py
# Whether a repeated measurement ran as the last one did, and how its values compare.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from datetime import datetime

from ..model import Quantity
from .plan import PlanStep

NOTABLE = 2.0  # a value that has halved or doubled since last time is pointed out


def _limit(text: str) -> tuple:
    """Limits compare by value: "> 1,00 MΩ" and ">1.00MΩ" are the same limit."""
    text = (text or "").strip()
    if not text:
        return ()
    quantity = Quantity.parse(text.replace(",", "."))
    if quantity.base_value is None:
        return (text.replace(" ", ""),)
    return quantity.qualifier, round(quantity.base_value, 9), quantity.base_unit


def _range(lower: str, upper: str) -> str:
    return " ".join(part for part in (lower, upper) if part) or "keine"


class RepeatCheckMixin:
    def origin_measurement(self, step: PlanStep):
        """The measurement of the last inspection this point stands for."""
        uuid, _, uid = step.origin.partition("/")
        return self.db.one(
            "SELECT m.*, c.closed_at FROM measurements m JOIN campaigns c ON c.id = m.campaign_id"
            " WHERE c.uuid=? AND m.device_uid=?", uuid, uid,
        )

    def point_measurement(self, step_id: int):
        return self.db.one(
            "SELECT * FROM measurements WHERE step_id=? ORDER BY local_time DESC, id DESC LIMIT 1",
            step_id,
        )

    def deviations(self, step: PlanStep, measurement_id: int) -> list[str]:
        """Limits and settings that differ from last time; what was not sent is not judged."""
        values = {value["key"]: value for value in self.values(measurement_id)}
        found = []
        for key, label, lower, upper in step.limits:
            value = values.get(key)
            if value is None:
                continue
            if (_limit(value["lower_limit"]), _limit(value["upper_limit"])) != (
                    _limit(lower), _limit(upper)):
                now = _range(value["lower_limit"], value["upper_limit"])
                found.append(f"Grenze {label}: {now} statt {_range(lower, upper)}")
        row = self.db.one("SELECT parameters_json FROM measurements WHERE id=?", measurement_id)
        now = {item["key"]: item["value"] for item in json.loads(row["parameters_json"] or "[]")}
        for key, value in step.parameters:
            if key in now and now[key] != value:
                found.append(f"{key}: {now[key]} statt {value}")
        return found

    def comparison(self, step: PlanStep, measurement_id: int) -> tuple[str, list[str]]:
        """Last time's values in a line, and those that have changed notably since."""
        origin = self.origin_measurement(step)
        if origin is None:
            return "", []
        before = {value["key"]: value for value in self.values(origin["id"])}
        parts, notable = [], []
        for value in self.values(measurement_id):
            old = before.get(value["key"])
            if old is None or value["key"] in ("question", "note"):
                continue
            parts.append(f"{old['label']} {old['raw']}")
            new, then = value["base_value"], old["base_value"]
            if new is not None and then is not None and new > 0 and then > 0:
                ratio = new / then
                if ratio >= NOTABLE or ratio <= 1 / NOTABLE:
                    change = "deutlich höher" if ratio > 1 else "deutlich niedriger"
                    notable.append(f"{value['label']} {change} als zuletzt")
        day = datetime.fromisoformat(origin["closed_at"])
        return (f"Zuletzt am {day:%d.%m.%Y}: " + "  ·  ".join(parts)) if parts else "", notable

    def repeat_blockers(self, campaign_id: int) -> list[str]:
        """Open points, and settings that differ from last time without a reason given."""
        points = self.points(campaign_id)
        missing = sum(row["status"] in ("pending", "active") for row, _ in points)
        problems = []
        if missing:
            problems.append(f"{missing} {'Punkt' if missing == 1 else 'Punkte'} der Wiederholung"
                            " offen: messen oder mit Begründung auslassen")
        for row, step in points:
            taken = self.point_measurement(row["id"]) if row["status"] == "done" else None
            if taken is not None and not row["note"] and self.deviations(step, taken["id"]):
                problems.append(f"Abweichende Einstellung bei „{step.title}“ ohne Begründung")
        return problems
