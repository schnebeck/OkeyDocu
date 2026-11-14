# OkeyDocu - okeydocu/campaign/repeat_checks.py
# Whether a repeated measurement ran as the last one did, and how its values compare.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from datetime import datetime

from ..l10n import day, in_language, plural, tr
from ..model import Quantity
from ..devices import setting_words
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
    return " ".join(part for part in (lower, upper) if part) or tr("none", context="limit")


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
                found.append(tr("Limit {label}: {now} instead of {before}",
                                label=label, now=now, before=_range(lower, upper)))
        row = self.db.one("SELECT parameters_json FROM measurements WHERE id=?", measurement_id)
        # Both sides in words: a push sends codes, an import from IZYTRONIQ brings German text.
        words = setting_words(self.db)
        now = {}
        for item in json.loads(row["parameters_json"] or "[]"):
            name, shown, said = words.say(item["key"], item["value"])
            now[name] = (shown, said)
        for key, value in step.parameters:
            name, before, said = words.say(key, value)
            current, current_said = now.get(name, (None, said))
            if current is None or current_said != said:
                continue  # not sent, or one side has no words yet: nothing to judge
            if current != before:
                found.append(tr("{name}: {now} instead of {before}",
                                name=name, now=current, before=before))
        return found

    def comparison(self, step: PlanStep, measurement_id: int) -> tuple[str, list[str]]:
        """Last time's values in a line, and those that have changed notably since."""
        origin = self.origin_measurement(step)
        if origin is None or not origin["closed_at"]:  # a point added on the way has no past
            return "", []
        before = {value["key"]: value for value in self.values(origin["id"])}
        parts, notable = [], []
        for value in self.values(measurement_id):
            old = before.get(value["key"])
            if old is None or value["key"] in ("question", "note"):
                continue
            parts.append(f"{in_language(old['label'])} {old['raw']}")
            new, then = value["base_value"], old["base_value"]
            if new is not None and then is not None and new > 0 and then > 0:
                ratio = new / then
                if ratio >= NOTABLE:
                    notable.append(tr("{label} notably higher than last time",
                                      label=value["label"]))
                elif ratio <= 1 / NOTABLE:
                    notable.append(tr("{label} notably lower than last time",
                                      label=value["label"]))
        if not parts:
            return "", notable
        closed = day(datetime.fromisoformat(origin["closed_at"]))
        return tr("Last time on {day}: {values}", day=closed, values="  ·  ".join(parts)), notable

    def repeat_blockers(self, campaign_id: int, strict: bool = True) -> list[str]:
        """Open points, and, `strict`, settings that differ from last time without a reason
        given. An open template asks no reasons."""
        points = self.points(campaign_id)
        missing = sum(row["status"] in ("pending", "active") for row, _ in points)
        problems = []
        if missing:
            problems.append(plural(
                missing, "{count} point of the repeat open: measure it or skip it with a reason",
                "{count} points of the repeat open: measure them or skip them with a reason"))
        for row, step in points:
            taken = self.point_measurement(row["id"]) if row["status"] == "done" else None
            if strict and taken is not None and not row["note"] and \
                    self.deviations(step, taken["id"]):
                problems.append(
                    tr("Different setting at “{title}” without a reason", title=step.title))
        return problems
