# OkeyDocu - okeydocu/campaign/template_learning.py
# What a campaign did differently from its open template, and taking that into the template.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A change names a point by its key in the template. New points are the readings that took
no point, and the points added during the campaign; their elements become nodes where the
template has none for them yet. Each change is taken over on its own."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from ..l10n import N_, tr
from .templates import NODE_FIELDS, is_template, point_data

NEW, DROPPED, ORDER, HINT = "new", "dropped", "order", "hint"
TEXTS = {NEW: N_("New point: {title}"), DROPPED: N_("Leave out: {title}"),
         ORDER: N_("Take over the order as measured"), HINT: N_("New hint at {title}: {text}")}


@dataclass(frozen=True)
class Change:
    kind: str
    title: str = ""
    text: str = ""
    key: str = ""  # the point's key in the template
    step_id: int | None = None
    measurement_id: int | None = None

    def label(self) -> str:
        return tr(TEXTS[self.kind], title=self.title, text=self.text)


class TemplateLearningMixin:
    def _campaign_points(self, campaign_id: int) -> list:
        """The campaign's points with the reading that took each, in the order of the points."""
        return [(row, step, self.point_measurement(row["id"]))
                for row, step in self.points(campaign_id)]

    def template_changes(self, campaign_id: int) -> list[Change]:
        campaign = self.campaign(campaign_id)
        template = self.template(campaign["plan_key"]) if is_template(campaign["plan_key"]) \
            else None
        if template is None:
            return []
        known = {point["key"] for point in template.points}
        found = []
        taken = self._campaign_points(campaign_id)
        kept = {step.key for _, step, _ in taken}
        for row, step, reading in taken:
            if step.key not in known:
                found.append(Change(NEW, step.title, key=step.key, step_id=row["id"]))
            elif row["status"] == "skipped":
                found.append(Change(DROPPED, step.title, key=step.key))
            elif reading is not None and reading["hint"] and reading["hint"] != step.hint:
                found.append(Change(HINT, step.title, reading["hint"], step.key,
                                    measurement_id=reading["id"]))
        found += [Change(DROPPED, point["title"], key=point["key"]) for point in template.points
                  if point["key"] not in kept]
        measured = [step.key for _, step, reading in sorted(
            (item for item in taken if item[2] is not None),
            key=lambda item: (item[2]["local_time"], item[2]["id"]))]
        planned = [point["key"] for point in template.points if point["key"] in measured]
        if measured != planned:
            found.append(Change(ORDER))
        return found

    def _node_of(self, template, assets: dict[int, str], asset_id: int | None) -> str:
        """The node of an element, made with the nodes above it where the template lacks it."""
        if asset_id is None:
            return template.nodes[0]["key"]
        if asset_id in assets:
            return assets[asset_id]
        row = self.db.asset(asset_id)
        parent = self._node_of(template, assets, row["parent_id"])
        key = f"n{len(template.nodes) + 1}"
        template.nodes.append({"key": key, "parent": parent, "asset": asset_id,
                               **{name: row[name] for name in NODE_FIELDS},
                               "features": self.db.asset_features(asset_id)})
        assets[asset_id] = key
        return key

    def learn(self, campaign_id: int, chosen: list[Change]) -> None:
        """Takes the chosen changes into the campaign's template."""
        campaign = self.campaign(campaign_id)
        template = self.template(campaign["plan_key"])
        taken = self._campaign_points(campaign_id)
        by_key = {point["key"]: point for point in template.points}
        assets = {step.asset_id: by_key[step.key]["node"] for _, step, _ in taken
                  if step.key in by_key and step.asset_id is not None}
        for change in chosen:
            if change.kind == NEW:
                step = next(s for r, s, _ in taken if r["id"] == change.step_id)
                node = self._node_of(template, assets, step.asset_id)
                key = f"p{len(template.points) + 1}_{change.step_id}"
                template.points.append(point_data(replace(step, key=key), node))
            elif change.kind == DROPPED:
                template.points = [p for p in template.points if p["key"] != change.key]
            elif change.kind == HINT:
                by_key[change.key]["hint"] = change.text
            elif change.kind == ORDER:
                times = {s.key: (m["local_time"], m["id"]) for _, s, m in taken if m is not None}
                order = sorted(times, key=times.get)
                template.points.sort(key=lambda p: (order.index(p["key"]) if p["key"] in order
                                                    else len(order)))
        template.learned.append({"campaign": campaign["title"],
                                 "date": date.today().isoformat()})
        self.save_template(template)
