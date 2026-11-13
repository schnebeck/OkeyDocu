# OkeyDocu - tests/test_reporting.py
# Templates with 0, 1 and n measurements, the PDF and the archive.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import subprocess
from datetime import timedelta

import pytest

from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.model import MeterMeasurement, Quantity, ResultValue, Verdict
from okeydocu.reporting.archive import ReportArchive, ReportError
from okeydocu.reporting.context import (
    ReportMeasurement,
    ReportStep,
    build_context,
    overall_verdict,
)
from okeydocu.reporting.pdf import render_pdf
from okeydocu.reporting.sign import Pkcs12Signer
from okeydocu.reporting.nodes import Footnoted
from okeydocu.reporting.template import (
    Fields,
    Notice,
    Paragraph,
    TemplateError,
    default_template_text,
    parse_template,
    resolve,
)

from .report_helpers import T0, closed_campaign

BLOCK = {
    "type": "steps",
    "blocks": [{"type": "measurements", "none": {"text": "Nicht gemessen: {{ step.note }}"}}],
}


def reading(text="2.00MΩ", function="riso", verdict=Verdict.PASSED, n=0):
    data = MeterMeasurement(
        uid=f"u{n}", function=function, taken_at=T0, verdict=verdict,
        results=(ResultValue("riso", "RISO", Quantity.parse(text), verdict, ">1.00MΩ"),),
    )
    return ReportMeasurement(data, T0 + timedelta(seconds=n))


def context(*measurements, status="done", note=""):
    step = ReportStep("Isolation", "riso", status, note, list(measurements))
    return {"campaign": {"simulated": False}, "steps": [step]}


def run(values):
    return resolve({"blocks": [BLOCK]}, values)


def test_zero_measurements_become_a_sentence():
    nodes = run(context(status="skipped", note="Kein Zugang"))
    assert nodes == [Paragraph("Nicht gemessen: Kein Zugang")]


def test_zero_measurements_can_be_hidden():
    block = {"type": "steps", "blocks": [{"type": "measurements", "none": {"hide": True}}]}
    assert resolve({"blocks": [block]}, context()) == []


def test_one_measurement_reads_like_a_form():
    (node,) = run(context(reading()))
    assert isinstance(node, Footnoted) and isinstance(node.body, Fields)
    assert ("<i>R</i><sub rise='30%'>ISO</sub>", "2,00\u202fMΩ  (Grenzwert >\u202f1,00\u202fMΩ)") in node.body.rows


def test_many_measurements_become_a_block_with_a_table_and_summary():
    head, node = run(context(reading("2.00MΩ", n=1), reading("900kΩ", n=2),
                             reading("5.00MΩ", n=3)))
    assert head.rows == [("Grenzwerte", "<i>R</i><sub rise='30%'>ISO</sub> &gt;\u202f1,00\u202fMΩ")]
    table = node.body
    assert len(table.rows) == 3
    assert table.summary[0][2] == "900\u202fkΩ"  # compared by value, not by text
    assert table.summary[1][2] == "5,00\u202fMΩ"


def test_functions_in_one_step_are_counted_separately():
    nodes = run(context(reading(function="rcd_time", n=1), reading(function="rcd_current", n=2),
                        reading(function="rcd_current", n=3)))
    kinds = [type(n).__name__ for n in nodes]
    assert kinds == ["Heading", "Footnoted", "Heading", "Fields", "Footnoted"]


def test_simulated_data_is_stamped_on_the_report():
    values = context(reading())
    values["campaign"]["simulated"] = True
    assert isinstance(run(values)[0], Notice)


def test_conditional_block():
    template = {"blocks": [{"type": "notice", "when": "device.overdue", "text": "Überfällig"}]}
    base = {"campaign": {}, "steps": []}
    assert resolve(template, {**base, "device": {"overdue": False}}) == []
    assert resolve(template, {**base, "device": {"overdue": True}}) == [Notice("Überfällig")]


def test_unknown_block_is_rejected():
    with pytest.raises(TemplateError, match="Unbekannter Block"):
        parse_template("blocks:\n  - type: magic\n")


def test_template_cannot_reach_python_internals():
    template = {"blocks": [{"type": "text", "text": "{{ ''.__class__.__mro__ }}"}]}
    with pytest.raises(TemplateError):
        resolve(template, {"campaign": {}, "steps": []}) and None
        _ = resolve(
            {"blocks": [{"type": "text", "text": "{{ ''.__class__.__mro__[1].__subclasses__() }}"}]},
            {"campaign": {}, "steps": []},
        )


@pytest.mark.parametrize(
    "steps,expected",
    [
        ([ReportStep("a", "riso", "done", "", [reading()])], "Bestanden"),
        ([ReportStep("a", "riso", "done", "", [reading(verdict=Verdict.FAILED)])], "Nicht bestanden"),
        ([ReportStep("a", "riso", "skipped", "x", [])], "Nicht vollständig geprüft"),
        ([ReportStep("a", "riso", "done", "", [])], "Nicht vollständig geprüft"),
        (
            [
                ReportStep("a", "riso", "done", "", [reading()]),
                ReportStep("b", "rlo", "skipped", "x", []),
            ],
            "Nicht vollständig geprüft",
        ),
    ],
)
def test_overall_verdict_never_overstates(steps, expected):
    assert overall_verdict(steps) == expected


def pdf_text(path):
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True
    ).stdout


def test_full_report_shows_all_three_cases(service, asset_id, plan):
    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    report = service.db.one("SELECT * FROM reports WHERE id=?", report_id)
    text = pdf_text(archive.path(report))
    assert "Musterbau GmbH" in text
    assert "Max" in text  # n: table with summary
    assert "Grenzwert" in text  # 1: fields
    assert "Anlage nicht zugänglich" in text  # 0: reason
    assert "Rekalibrierung fällig" in text
    assert "überfällig" not in text
    assert "Nicht vollständig geprüft" in text
    assert "MΩ" in text and "Ω" in text
    assert "Seite 1 von" in text
    assert "SIMULIERT" not in text


def test_simulated_report_says_so_and_cannot_be_signed(service, asset_id, plan, tmp_path):
    campaign = closed_campaign(service, asset_id, plan)
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    report = service.db.one("SELECT * FROM reports WHERE id=?", report_id)
    assert "SIMULIERTE MESSWERTE" in pdf_text(archive.path(report))
    with pytest.raises(ReportError, match="simulierten"):
        archive.sign(report_id, Pkcs12Signer(tmp_path / "x.p12", "x"))


def test_open_campaign_produces_no_archived_report(service, asset_id, plan):
    campaign = service.start(asset_id, plan, "T", "P", "simulator", SimulatedMeter())
    with pytest.raises(ReportError, match="abgeschlossenen"):
        ReportArchive(service).generate(campaign, "Standard", default_template_text())


def test_archive_detects_a_changed_file(service, asset_id, plan):
    campaign = closed_campaign(service, asset_id, plan)
    archive = ReportArchive(service)
    report = service.db.one(
        "SELECT * FROM reports WHERE id=?",
        archive.generate(campaign, "Standard", default_template_text()),
    )
    assert archive.is_intact(report)
    with archive.path(report).open("ab") as stream:
        stream.write(b"x")
    assert not archive.is_intact(report)


def test_archive_keeps_the_template_that_was_used(service, asset_id, plan):
    campaign = closed_campaign(service, asset_id, plan)
    body = default_template_text()
    report_id = ReportArchive(service).generate(campaign, "Standard", body)
    assert service.db.one("SELECT * FROM reports WHERE id=?", report_id)["template_body"] == body


def test_context_contains_the_stored_reading(service, asset_id, plan):
    campaign = closed_campaign(service, asset_id, plan)
    values = build_context(service, campaign)
    assert values["device"]["overdue"] is True
    assert len(values["steps"][0].measurements) == 3


def test_field_labels_are_rendered_too():
    template = {"blocks": [{"type": "fields", "rows": [["{{ asset.kind }}", "Presse"]]}]}
    (node,) = resolve(template, {"campaign": {}, "steps": [], "asset": {"kind": "Maschine"}})
    assert node.rows == [("Maschine", "Presse")]


def test_report_without_instrument_has_no_device_section(service, asset_id):
    campaign = service.create(asset_id, "Handmessung", "Prüfer")
    service.add_measurement(campaign, "other", [], T0)
    service.close(campaign)
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    text = pdf_text(archive.path(service.db.one("SELECT * FROM reports WHERE id=?", report_id)))
    assert "Messgerät" not in text and "Uhrenversatz" not in text
    assert "{{" not in text


def test_photo_caption_names_its_measurement(tmp_path):
    from okeydocu.reporting.template import Photos

    measurement = reading()
    measurement.photos.append(tmp_path / "a.jpg")
    block = {"type": "steps", "blocks": [{"type": "photos"}]}
    (node,) = resolve({"blocks": [block]}, context(measurement))
    assert isinstance(node, Photos)
    assert node.items == [(tmp_path / "a.jpg", "<i>R</i><sub rise='30%'>ISO</sub>"
                           " – Isolationswiderstand · 01.03.2026 10:00:00", [], "", [])]


def test_a_defect_photo_says_so_and_names_its_marks(tmp_path):
    from okeydocu.campaign.photo_marks import PhotoMark
    from okeydocu.reporting.template import Photos

    measurement = reading()
    path = tmp_path / "a.jpg"
    measurement.photos.append(path)
    marks = [PhotoMark(1, 0.1, 0.1, 0.2, 0.2, "Isolierung angeschmort"),
             PhotoMark(2, 0.5, 0.5, 0.1, 0.1)]
    measurement.photo_notes[str(path)] = ("defect", marks)
    block = {"type": "steps", "blocks": [{"type": "photos"}]}
    (node,) = resolve({"blocks": [block]}, context(measurement))
    assert isinstance(node, Photos)
    _, caption, drawn, role, texts = node.items[0]
    assert caption.startswith("<b>Mangel:</b> <i>R</i>")
    assert texts == ["(1) Isolierung angeschmort"]
    assert (drawn, role) == (marks, "defect")


def test_pdf_renders_into_memory():
    buffer = io.BytesIO()
    render_pdf(run(context(reading())), buffer)
    assert buffer.getvalue().startswith(b"%PDF")
