# OkeyDocu - okeydocu/campaign/templates.py
# Campaign templates: the structure and the points of an inspection, kept to be taken again.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A template keeps the element tree below the installation it was made on (its blueprint) and
the points measured there, in the order they were measured, but no measured value. Its points
are the points of a repeat inspection tied to blueprint nodes instead of elements, so it fits
another installation of the same build as well. It lies in the table of test plans under a key
of its own and is told apart from a plan by that key.

Open, a template is edited all the way and learns from every campaign confirmed with it; in
series mode its points are fixed and a deviation needs a reason."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import date

import yaml

from .plan import PlanStep
from .point_plans import TEMPLATE_PREFIX as PREFIX
from .point_plans import is_template
OPEN, SERIES = "open", "series"
NODE_FIELDS = ("kind", "name", "identifier", "manufacturer", "type", "comment")


@dataclass
class CampaignTemplate:
    key: str
    title: str
    mode: str = OPEN
    root_asset: int | None = None  # the installation it was made on
    nodes: list[dict] = field(default_factory=list)  # key, parent, asset, NODE_FIELDS, features
    points: list[dict] = field(default_factory=list)  # a plan step's fields with `node`
    learned: list[dict] = field(default_factory=list)  # campaign title and date, oldest first

    def node(self, key: str) -> dict | None:
        return next((node for node in self.nodes if node["key"] == key), None)

    def steps(self, assets: dict[str, int]) -> tuple[PlanStep, ...]:
        """The points as plan steps at the elements `assets` maps the nodes to."""
        found = []
        for point in self.points:
            data = {k: v for k, v in point.items() if k != "node"}
            found.append(replace(PlanStep.from_dict(data), asset_id=assets.get(point["node"])))
        return tuple(found)

    def body(self) -> str:
        return yaml.safe_dump({"kind": "campaign_template", "title": self.title, "mode": self.mode,
                               "root_asset": self.root_asset, "nodes": self.nodes,
                               "points": self.points, "learned": self.learned},
                              allow_unicode=True, sort_keys=False)

    @classmethod
    def parse(cls, key: str, body: str) -> "CampaignTemplate":
        data = yaml.safe_load(body) or {}
        return cls(key, data.get("title", ""), data.get("mode", OPEN), data.get("root_asset"),
                   list(data.get("nodes") or []), list(data.get("points") or []),
                   list(data.get("learned") or []))


def point_data(step: PlanStep, node: str) -> dict:
    """What a template keeps of a plan step: everything but the element, which is a node."""
    plain = json.loads(json.dumps(step.to_dict(), ensure_ascii=False))
    data = {k: v for k, v in plain.items() if k != "asset_id" and v not in ("", [], None)}
    return {**data, "node": node}


class TemplateMixin:
    def templates(self) -> list[CampaignTemplate]:
        rows = self.db.query("SELECT * FROM plans WHERE key LIKE ? ESCAPE '!'"
                             " ORDER BY title COLLATE NOCASE", PREFIX.replace("_", "!_") + "%")
        return [CampaignTemplate.parse(row["key"], row["body"]) for row in rows]

    def template(self, key: str) -> CampaignTemplate | None:
        row = self.db.one("SELECT * FROM plans WHERE key=?", key)
        return CampaignTemplate.parse(key, row["body"]) if row else None

    def save_template(self, template: CampaignTemplate) -> None:
        self.db.save_plan(template.key, template.title, template.body())

    def delete_template(self, key: str) -> None:
        self.db.delete_plan(key)

    def blueprint(self, root_id: int) -> tuple[list[dict], dict[int, str]]:
        """The element tree from `root_id` down as nodes, and which node each element is."""
        nodes, keys = [], {}
        for number, asset_id in enumerate(self.subtree(root_id), start=1):
            row = self.db.asset(asset_id)
            keys[asset_id] = f"n{number}"
            node = {"key": keys[asset_id], "parent": keys.get(row["parent_id"]),
                    "asset": asset_id, **{name: row[name] for name in NODE_FIELDS}}
            node["features"] = self.db.asset_features(asset_id)
            nodes.append(node)
        return nodes, keys

    def template_from(self, campaign_id: int, title: str, mode: str = OPEN) -> str:
        """A new template from a campaign: its installation's tree and its points."""
        campaign = self.campaign(campaign_id)
        nodes, keys = self.blueprint(campaign["asset_id"])
        plan = self.repeat_plan(campaign_id)
        points = [point_data(replace(step, key=f"p{number}"), keys.get(step.asset_id, "n1"))
                  for number, step in enumerate(plan.steps, start=1)]
        template = CampaignTemplate(PREFIX + uuid.uuid4().hex[:10], title, mode,
                                    campaign["asset_id"], nodes, points,
                                    [{"campaign": campaign["title"],
                                      "date": date.today().isoformat()}])
        self.save_template(template)
        return template.key

    def template_mode(self, plan_key: str | None) -> str | None:
        """Open or series for a template campaign; None for anything else."""
        template = self.template(plan_key) if is_template(plan_key) else None
        return template.mode if template else None
