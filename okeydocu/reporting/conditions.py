# OkeyDocu - okeydocu/reporting/conditions.py
# The surroundings a test was taken in, as one line of the report's head.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The latest measurement of the surroundings stands for the test: when and with which
instrument it was taken is said with it, since its figures are worth only as much as the
place and time they came from. The measurement keeps its row among the others as well."""

from __future__ import annotations

from datetime import datetime

from ..l10n import decimal, moment, tr

FUNCTION = "ambient"


def conditions_text(service, campaign_id: int, names: dict[str, str]) -> str:
    """`names` tells by serial number what each instrument is called in the report."""
    rows = [row for row in service.measurements(campaign_id) if row["function"] == FUNCTION]
    if not rows:
        return ""
    latest = max(rows, key=lambda row: row["local_time"])
    values = {result.key: result.quantity.base_value
              for result in service.load_measurement(latest).results
              if result.quantity is not None and result.quantity.base_value is not None}
    if "t_air" not in values:
        return ""
    text = tr("{temperature} \u00b0C", temperature=decimal(values["t_air"], 1))
    if "rh" in values:
        text += ", " + tr("{humidity} % r.H.", humidity=decimal(values["rh"], 0))
    when = moment(datetime.fromisoformat(latest["local_time"]))
    instrument = names.get(latest["device_serial"] or "", "")
    said = tr("measured {moment} with {instrument}", moment=when, instrument=instrument) \
        if instrument else tr("measured {moment}", moment=when)
    return f"{text}, {said}"
