# OkeyDocu - okeydocu/campaign/point_plans.py
# Which campaigns hold points to be taken in any order: repeat inspections and templates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

REPEAT = "repeat"  # the plan key of a campaign whose steps came from the last inspection
TEMPLATE_PREFIX = "template_"  # the plan key of a campaign template begins so


def is_template(plan_key: str | None) -> bool:
    return bool(plan_key) and plan_key.startswith(TEMPLATE_PREFIX)


def has_points(plan_key: str | None) -> bool:
    """Whether a campaign's steps are points taken in any order: a repeat or a template."""
    return plan_key == REPEAT or is_template(plan_key)
