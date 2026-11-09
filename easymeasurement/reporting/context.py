# EasyMeasurement - easymeasurement/reporting/context.py
# Collects everything a report may show into one plain data structure.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ..campaign.service import MANUAL, CampaignService
from ..model import FUNCTION_LABELS, SIGHT_CHECK_FUNCTION, MeterMeasurement, Verdict
from .attached import Attached, places, sort_attached
from .language import day, feature_name, kind_name, moment, tr

VERDICT_TEXT = {
    Verdict.PASSED: "bestanden",
    Verdict.FAILED: "nicht bestanden",
    Verdict.NOT_EVALUATED: "nicht bewertet",
}

def _features(db, asset) -> list[tuple[str, str]]:
    """The features noted on the element, in the order of its kind; empty ones stay out."""
    kind, values = db.kind(asset["kind"]), db.asset_features(asset["id"])
    return [(feature_name(feature.key, feature.label),
             f"{values[feature.key]} {feature.unit}".strip())
            for feature in (kind.features if kind else ()) if values.get(feature.key)]


@dataclass
class ReportMeasurement:
    data: MeterMeasurement
    local_time: datetime
    photos: list[Path] = field(default_factory=list)
    manual: bool = False  # typed in, not read from an instrument
    edited: bool = False  # something other than the reading was overwritten
    attached: Attached = field(default_factory=Attached)


@dataclass
class ReportStep:
    title: str
    function: str
    status: str
    note: str
    measurements: list[ReportMeasurement] = field(default_factory=list)


def overall_verdict(steps: list[ReportStep]) -> str:
    """Summarise honestly: a skipped or empty step is not a pass."""
    verdicts = [m.data.verdict for step in steps for m in step.measurements]
    if Verdict.FAILED in verdicts:
        return tr("Nicht bestanden")
    complete = bool(steps) and all(
        s.status == "done" and s.measurements for s in steps
    )
    if complete and all(v is Verdict.PASSED for v in verdicts):
        return tr("Bestanden")
    return tr("Nicht vollständig geprüft")


def _add_answers(steps: list[ReportStep], title: str, measured: list) -> None:
    """Answers in a row form one table under the name of their plan."""
    last = steps[-1] if steps else None
    if last and last.function == SIGHT_CHECK_FUNCTION and last.title == title:
        last.measurements.extend(measured)
    else:
        steps.append(ReportStep(tr(title), SIGHT_CHECK_FUNCTION, "done", "", measured))


def build_context(service: CampaignService, campaign_id: int) -> dict:
    campaign = service.campaign(campaign_id)
    asset = service.db.asset(campaign["asset_id"])
    customer = service.db.customer(asset["customer_id"])
    identity = service.identity(campaign_id)

    def load(row) -> ReportMeasurement:
        attached = sort_attached(service, service.attachments(campaign_id, measurement_id=row["id"]))
        return ReportMeasurement(
            service.load_measurement(row),
            datetime.fromisoformat(row["local_time"]),
            service.photo_paths(row["id"]) + attached.images,
            manual=row["source"] == MANUAL,
            # Who measured is registered, but it says nothing about the result.
            edited=any(c["field"] != "operator" for c in service.measurement_changes(row["id"])),
            attached=attached,
        )

    steps = []
    for row in service.steps(campaign_id):
        plan_step = service.plan_step(row)
        measured = [load(m) for m in service.measurements(campaign_id, row["id"])]
        if plan_step.kind == "note":
            continue
        if plan_step.kind == "check" and row["status"] == "done":
            _add_answers(steps, row["plan_title"], measured)
            continue
        steps.append(ReportStep(tr(plan_step.title), plan_step.function, row["status"], row["note"],
                                measured))

    # Without a plan, measurements are simply grouped by what was measured.
    loose: dict[str, list[ReportMeasurement]] = {}
    for row in service.open_measurements(campaign_id):
        loose.setdefault(row["function"], []).append(load(row))
    for function, measured in loose.items():
        steps.append(ReportStep(function_label(function), function, "done", "", measured))

    return {
        "customer": dict(customer),
        "asset": {**dict(asset), "kind_text": kind_name(
                      asset["kind"], service.db.kind_labels().get(asset["kind"], "")),
                  "features": _features(service.db, asset)},
        "campaign": {
            "title": campaign["title"],
            "tester": campaign["tester"],
            "signature": campaign["signature"],
            "plan": campaign["plan_title"],
            "uuid": campaign["uuid"],
            "started": _date_text(campaign["started_at"]),
            "closed": _date_text(campaign["closed_at"]),
            "clock_offset_s": round(campaign["clock_offset_s"]),
            "clock_summary": clock_summary(campaign, service.clock_checks(campaign_id)),
            "seal": campaign["seal"],
            "simulated": campaign["driver"] == "simulator",
            "draft": campaign["status"] == "open",
        },
        "device": {
            "manufacturer": identity.manufacturer,
            "model": identity.model,
            "serial_no": identity.serial_no,
            "firmware": identity.firmware,
            "calibrated_on": _day(identity.calibrated_on),
            "recalibration_due": _day(identity.recalibration_due),
            "overdue": identity.calibration_overdue(_reference_day(campaign)),
        },
        "steps": steps,
        "places": places(service, campaign_id),
        "verdict": overall_verdict(steps),
    }


def clock_summary(campaign, checks) -> str:
    """Say which offset the times rest on, including any change along the way."""
    notes = []
    for check in checks:
        moment = _date_text(check["checked_at"])
        if check["kind"] == "set":
            notes.append(tr("am {moment} gestellt (Abweichung vorher {offset} s)").format(
                moment=moment, offset=f"{check['offset_before_s']:+.0f}"))
        elif check["kind"] == "manual":
            notes.append(tr("Versatz am {moment} von Hand auf {offset} s festgelegt").format(
                moment=moment, offset=f"{check['offset_s']:+.0f}"))
    offset = round(campaign["clock_offset_s"])
    if offset:
        notes.append(tr("Versatz {offset} s, die Zeiten unten sind korrigiert").format(
            offset=f"{offset:+d}"))
    return "; ".join(notes) or tr("Abweichung 0 s")


def _reference_day(campaign) -> date:
    return datetime.fromisoformat(campaign["started_at"]).date()


def _day(value: date | None) -> str:
    return day(value)


def _date_text(value: str | None) -> str:
    return moment(datetime.fromisoformat(value)) if value else "–"


def function_label(key: str) -> str:
    return tr(FUNCTION_LABELS.get(key, key))
