# EasyMeasurement - tests/report_helpers.py
# A closed campaign on a fixed timeline for the report tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

from easymeasurement.devices.simulator import SimulatedMeter

T0 = datetime(2026, 3, 1, 10, 0, 0)


def closed_campaign(service, asset_id, plan, driver_key="simulator"):
    meter = SimulatedMeter(seed=3, overdue=True)
    campaign = service.start(asset_id, plan, "Wiederholungsprüfung", "Prüfer", driver_key, meter)
    # The timeline below runs earlier than the real start.
    service.db.execute("UPDATE campaigns SET stored_since=NULL WHERE id=?", campaign)
    steps = service.steps(campaign)
    service.confirm_setup(steps[0]["id"], now=T0)
    for n in range(3):
        meter.simulate_measurement("rlo", at=T0 + timedelta(seconds=10 * n))
    service.finish_step(steps[0]["id"], now=T0 + timedelta(minutes=1))
    service.confirm_setup(steps[1]["id"], now=T0 + timedelta(minutes=2))
    meter.simulate_measurement("riso", at=T0 + timedelta(minutes=3))
    service.finish_step(steps[1]["id"], now=T0 + timedelta(minutes=4))
    service.collect(campaign, meter)
    for step in steps[2:]:
        service.skip_step(step["id"], "Anlage nicht zugänglich")
    service.close(campaign)
    return campaign
