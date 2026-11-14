# OkeyDocu - okeydocu/campaign/template_use.py
# Taking a campaign template: its elements found or made, its points laid into the campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""On the installation the template was made on, every node is the element it came from; one
deleted since is made again. On another installation the tree below it is made anew, with the
names and identifiers given. The points then lie in the campaign like those of a repeat
inspection. Open, the campaign may add, move and remove points as it goes."""

from __future__ import annotations

import json

from ..model import SIGHT_CHECK_FUNCTION
from ..vocabulary import function_symbol
from .plan import Plan, PlanStep
from .templates import NODE_FIELDS, CampaignTemplate


class TemplateUseMixin:
    def copy_needed(self, key: str, asset_id: int) -> bool:
        template = self.template(key)
        return template is not None and template.root_asset != asset_id

    def _make_node(self, node: dict, parent_id: int, named: tuple[str, str] | None) -> int:
        parent = self.db.asset(parent_id)
        fields = {name: node.get(name) or "" for name in NODE_FIELDS[2:]}
        if named is not None:
            fields["identifier"] = named[1]
        asset_id = self.db.add_asset(parent["customer_id"], node["kind"],
                                     named[0] if named else node["name"], parent_id, **fields)
        if node.get("features"):
            self.db.set_asset_features(asset_id, dict(node["features"]))
        return asset_id

    def _elements(self, template: CampaignTemplate, root_id: int,
                  names: dict[str, tuple[str, str]] | None) -> dict[str, int]:
        """Every node to an element below `root_id`, made where it is missing."""
        same = template.root_asset == root_id
        existing = set(self.subtree(root_id))
        assets: dict[str, int] = {}
        for node in template.nodes:
            if node.get("parent") is None:
                assets[node["key"]] = root_id
            elif same and node.get("asset") in existing:
                assets[node["key"]] = node["asset"]
            else:
                parent = assets.get(node["parent"], root_id)
                assets[node["key"]] = self._make_node(node, parent, (names or {}).get(node["key"]))
        return assets

    def use_template(self, campaign_id: int, key: str,
                     names: dict[str, tuple[str, str]] | None = None) -> None:
        """Lays the template's points into the campaign; `names` renames the nodes made anew,
        as (name, identifier) by node key."""
        template = self.template(key)
        campaign = self.campaign(campaign_id)
        assets = self._elements(template, campaign["asset_id"], names)
        self.assign_plan(campaign_id, Plan(key, template.title, True, template.steps(assets)))
        self.rematch(campaign_id)

    # Editing the points of an open template campaign -------------------------------------

    def add_point_from(self, measurement_id: int) -> int:
        """A reading that took no point becomes a point of its own, taken by it."""
        row = self.db.one("SELECT m.*, c.uuid FROM measurements m JOIN campaigns c"
                          " ON c.id = m.campaign_id WHERE m.id=?", measurement_id)
        values = self.values(measurement_id)
        check = row["function"] == SIGHT_CHECK_FUNCTION
        question = next((v["raw"] for v in values if v["key"] == "question"), "")
        step = PlanStep(
            key=f"a{measurement_id}", kind="check" if check else "measure",
            title=row["step_name"] or (question if check else function_symbol(row["function"])),
            function=row["function"], asset_id=row["asset_id"], question=question,
            limits=tuple((v["key"], v["label"], v["lower_limit"], v["upper_limit"])
                         for v in values if v["lower_limit"] or v["upper_limit"]),
            parameters=tuple((p["key"], p["value"])
                             for p in json.loads(row["parameters_json"] or "[]")),
            origin=f"{row['uuid']}/{row['device_uid']}", hint=row["hint"], remark=row["comment"])
        campaign = self.campaign(row["campaign_id"])
        with self.db.transaction() as connection:
            last = connection.execute("SELECT max(position) FROM steps WHERE campaign_id=?",
                                      (row["campaign_id"],)).fetchone()[0]
            cursor = connection.execute(
                "INSERT INTO steps (campaign_id, position, plan_json, plan_title, status)"
                " VALUES (?, ?, ?, ?, 'done')",
                (row["campaign_id"], (last or 0) + 1,
                 json.dumps(step.to_dict(), ensure_ascii=False), campaign["plan_title"]))
            connection.execute("UPDATE measurements SET step_id=?, assignment='manual'"
                               " WHERE id=?", (cursor.lastrowid, measurement_id))
        return cursor.lastrowid

    def move_point(self, step_id: int, offset: int) -> None:
        """One place up (-1) or down (+1) among the campaign's points."""
        row = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        ordered = [r["id"] for r, _ in self.points(row["campaign_id"])]
        index = ordered.index(step_id)
        other = index + offset
        if not 0 <= other < len(ordered):
            return
        neighbour = self.db.one("SELECT position FROM steps WHERE id=?", ordered[other])
        with self.db.transaction() as connection:
            connection.execute("UPDATE steps SET position=-1 WHERE id=?", (step_id,))
            connection.execute("UPDATE steps SET position=? WHERE id=?",
                               (row["position"], ordered[other]))
            connection.execute("UPDATE steps SET position=? WHERE id=?",
                               (neighbour["position"], step_id))

    def remove_point(self, step_id: int) -> None:
        """Only an open point goes; one that took a reading stays."""
        if self.db.one("SELECT 1 FROM measurements WHERE step_id=?", step_id) is None:
            self.db.execute("DELETE FROM steps WHERE id=?", step_id)

    def next_point(self, campaign_id: int, after_step: int | None) -> int | None:
        """The element of the next open point after `after_step`, in the order of the points,
        starting again at the first."""
        points = self.points(campaign_id)
        ids = [row["id"] for row, _ in points]
        start = ids.index(after_step) + 1 if after_step in ids else 0
        for row, step in points[start:] + points[:start]:
            if row["status"] == "pending" and step.asset_id is not None:
                return step.asset_id
        return None


def renamed(template: CampaignTemplate) -> list[dict]:
    """The nodes made anew on another installation, with their depth below the root."""
    depth = {}
    found = []
    for node in template.nodes:
        if node.get("parent") is None:
            depth[node["key"]] = 0
            continue
        depth[node["key"]] = depth.get(node["parent"], 0) + 1
        found.append({**node, "depth": depth[node["key"]]})
    return found
