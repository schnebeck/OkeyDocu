# EasyMeasurement - easymeasurement/importing/izytron.py
# Imports one day of testing from a copy of an IZYTRON.IQ database as a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reads the database strictly read-only. Usage:

    python -m easymeasurement.importing.izytron COPY.sqlite --offset -648

`--offset` says how far the instrument's clock was ahead of local time that day,
in seconds. It depends on the date, because the clock has no daylight saving.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from ..campaign.service import IMPORTED, CampaignService
from .izytron_measurements import _check_measurement, _device_measurement, _time
from .izytron_source import ImportFailed, _import_tree, _is_structure, _location, _Source

SOURCE = "import:izytron"
FROM_DEVICE = "CommonImportFromDevice"


@dataclass
class ImportResult:
    campaign_id: int
    measurements: int
    checks: int
    assets: int


def import_day(
    service: CampaignService, path: Path, clock_offset_s: float, title: str = ""
) -> ImportResult:
    """Import everything in the database as one campaign, open for review."""
    source = _Source(path)
    steps = source.steps()
    if not steps:
        raise ImportFailed("Die Datenbank enthält keine Prüfungen.")
    known = service.db.one(
        "SELECT 1 FROM measurements WHERE source=? AND device_uid=?", SOURCE, steps[0]["ID"].lower()
    )
    if known:
        raise ImportFailed("Diese Prüfungen wurden schon importiert.")

    customer = source.customer()
    name = customer["Designation"] or "Ohne Namen"
    same = [row["id"] for row in service.db.customers() if row["name"].casefold() == name.casefold()]
    customer_id = same[0] if same else service.db.add_customer(
        name, customer["Street"] or "", customer["Postal_Code"] or "", customer["City"] or "",
    )
    assets = _import_tree(source, service, customer_id)
    root = next(
        asset for key, asset in assets.items()
        if not _is_structure(source.by_id.get((source.nodes[key]["Parent_ID"] or "").lower()))
    )
    information = json.loads(steps[0]["Testing_Device_Information"] or "{}")
    for step in steps:
        if step["Kind"] == FROM_DEVICE:
            information = json.loads(step["Testing_Device_Information"] or "{}")
            break
    identity = source.instrument(information)
    testers = Counter(step["Tester_Name"] for step in steps if step["Tester_Name"])
    tester = max(testers, key=len) if testers else ""
    day = _time(steps[0]["Date"]).date()
    campaign_id = service.create(
        root, title or f"Prüfung vom {day:%d.%m.%Y} (aus IZYTRON)", tester, None, IMPORTED,
        identity, clock_offset_s,
    )
    service.db.execute(
        "UPDATE clock_checks SET kind='manual' WHERE campaign_id=?", campaign_id
    )
    offset = timedelta(seconds=clock_offset_s)
    moments, measurements, checks = [], 0, 0
    runs: dict[str, int] = {}  # a testing entered on the PC is one run of its steps
    for step in steps:
        data = json.loads(step["Measurement_Data"] or "{}")
        location = _location(source, step["Abstract_Device_ID"])
        asset_id = assets.get(step["Abstract_Device_ID"].lower())
        from_device = step["Kind"] == FROM_DEVICE
        if from_device:
            measurement = _device_measurement(step, data, location)
            local_time, device_time = measurement.taken_at - offset, measurement.taken_at
            measurements += 1
        else:
            # Entered on the PC, so this is local time already.
            measurement = _check_measurement(step, data, location)
            local_time, device_time = measurement.taken_at, None
            checks += 1
        measurement_id = service.insert_imported(
            campaign_id, measurement, SOURCE, local_time, device_time, identity,
            clock_offset_s if from_device else None, asset_id,
        )
        if not from_device:
            testing = step["Testing_ID"].lower()
            if testing not in runs:
                runs[testing] = service.add_run(
                    campaign_id, step["Name"] or step["Kind"], step["Kind"], local_time, testing
                )
            service.join_run(measurement_id, runs[testing], step["Step_Description"] or "")
        moments.append(local_time)
    service.date_import(campaign_id, min(moments))
    return ImportResult(campaign_id, measurements, checks, len(assets))


def main() -> None:
    from ..paths import data_dir
    from ..store import Database

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--offset", type=float, required=True)
    parser.add_argument("--title", default="")
    arguments = parser.parse_args()
    root = data_dir()
    database = Database(root / "easymeasurement.sqlite")
    result = import_day(
        CampaignService(database, root), arguments.database, arguments.offset, arguments.title
    )
    print(
        f"Kampagne {result.campaign_id}: {result.measurements} Messungen,"
        f" {result.checks} Prüfpunkte, {result.assets} Anlagenteile"
    )


if __name__ == "__main__":
    main()
