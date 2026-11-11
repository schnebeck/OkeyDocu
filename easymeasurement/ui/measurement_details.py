# EasyMeasurement - easymeasurement/ui/measurement_details.py
# What was measured where and how: settings, conditions, every figure and its role.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument sends its whole result block. This view shows all of it and says of each
figure what it stands for and whether the report shows it, so nothing that was left out of
a report is out of reach. The instrument's own record follows on request."""

from __future__ import annotations

import json
from datetime import datetime
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from xml.sax.saxutils import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QScrollArea, QToolButton

from ..devices import setting_words
from ..l10n import N_, moment, tr
from ..model import CONDUCTOR, Verdict, conductor_of
from ..reporting.context import VERDICT_TEXT
from ..reporting.language import value_text
from ..vocabulary import (
    ROLE_TEXT,
    conductors,
    counts,
    function_markup,
    outcome_text,
    result_markup,
    role,
)
from .common import AppContext
from .measurement_detail import capture_text
from .overlay import Overlay

HEADERS = (N_("Symbol"), N_("Reading"), N_("Limit"), N_("Verdict"), N_("Role"),
           N_("In the report"))


def _rows(rows: list[tuple[str, str]]) -> str:
    """Label and value, both already marked up."""
    cells = "".join(f"<tr><td style='padding-right:14px'><b>{label}</b></td><td>{value}</td>"
                    "</tr>" for label, value in rows if value)
    return f"<table cellspacing='2'>{cells}</table>" if cells else ""


def _section(title: str, body: str) -> str:
    return f"<h4>{escape(title)}</h4>{body}" if body else ""


def _figure(text: str) -> str:
    return escape(value_text(outcome_text(text)))


def _limit(result) -> str:
    parts = [_figure(result.lower_limit), _figure(result.upper_limit)]
    if result.setpoint:
        parts.append(escape(tr("expected")) + " " + _figure(result.setpoint))
    return " ".join(part for part in parts if part)


def _results(data) -> str:
    passed = data.verdict is Verdict.PASSED
    head = "".join(f"<th align='left' style='padding-right:14px'>{escape(tr(title))}</th>"
                   for title in HEADERS)
    lines = []
    for result in data.results:
        found = role(data.function, result.key, result.quantity.raw)
        shown = counts(data.function, result.key, result.quantity.raw, passed)
        verdict = ""
        if result.verdict is not Verdict.NOT_EVALUATED:
            verdict = tr(VERDICT_TEXT[result.verdict])
        cells = (result_markup(result.key, result.label), _figure(result.quantity.raw) or "–",
                 _limit(result), escape(verdict), escape(tr(ROLE_TEXT[found])),
                 escape(outcome_text("yes" if shown else "no")))
        lines.append("<tr>" + "".join(f"<td style='padding-right:14px'>{cell}</td>"
                                      for cell in cells) + "</tr>")
    return f"<table cellspacing='2'><tr>{head}</tr>{''.join(lines)}</table>" if lines else ""


def details_html(app: AppContext, row) -> str:
    service = app.service
    data = service.load_measurement(row)
    root = service.campaign(row["campaign_id"])["asset_id"]
    local = datetime.fromisoformat(row["local_time"])
    head = (f"<p style='font-size:large'><b>{function_markup(data.function)}</b></p>"
            f"<p>{escape(moment(local, seconds=True))} · "
            f"{escape(tr(VERDICT_TEXT[data.verdict]))}</p>")
    element = service.place_path(row["asset_id"], root) if row["asset_id"] else ""
    location = " / ".join(data.location)
    where = _rows([
        (escape(tr("Element")), escape(element)),
        (escape(tr("Location in the equipment")), escape(location if location != element else "")),
        (escape(tr("Conductors")), conductors(conductor_of(data.parameters))),
    ])
    instrument = row["device_time"] and datetime.fromisoformat(row["device_time"])
    how = _rows([
        (escape(tr("Capture")), escape(capture_text(row))),
        (escape(tr("Serial number")), escape(row["device_serial"])),
        (escape(tr("Firmware")), escape(row["firmware"])),
        (escape(tr("Time on the instrument")),
         escape(moment(instrument, seconds=True)) if instrument and instrument != local else ""),
        (escape(tr("Inspector")), escape(data.operator)),
    ])
    words = setting_words(app.db)
    settings = _rows([(escape(name), conductors(value)) for name, value, _ in (
        words.say(parameter.key, parameter.value) for parameter in data.parameters
        if parameter.key != CONDUCTOR)])
    remarks = _rows([(escape(tr("Remark")), escape(data.comment).replace("\n", "<br>")),
                     (escape(tr("How to measure here")), escape(row["hint"]))])
    return "".join([head, _section(tr("Where"), where), _section(tr("How"), how),
                    _section(tr("Settings of the instrument"), settings),
                    _section(tr("Results"), _results(data)), _section(tr("Remarks"), remarks)])


def readable_record(raw: str) -> str:
    """The instrument's record laid out in lines, as far as it is XML or JSON."""
    try:
        return minidom.parseString(raw).toprettyxml(indent="  ")
    except (ExpatError, TypeError, ValueError):
        pass
    try:
        return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return raw


class MeasurementDetails(Overlay):
    def __init__(self, app: AppContext, measurement_id: int, parent=None):
        super().__init__(tr("How it was measured"), parent, width=780)
        row = app.db.one("SELECT * FROM measurements WHERE id=?", measurement_id)
        self.ok_button.setText(tr("Close"))
        self.cancel_button.hide()
        self.text = QLabel(details_html(app, row))
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.text.setWordWrap(True)
        self.text.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.text)
        scroll.setMinimumHeight(460)
        self.body.addWidget(scroll, 1)
        self.record = QPlainTextEdit(readable_record(row["raw_data"]))
        self.record.setReadOnly(True)
        self.record.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.record.setMinimumHeight(200)
        self.record.hide()
        if row["raw_data"]:
            toggle = QToolButton(text=tr("Show the instrument's record"), checkable=True)
            toggle.toggled.connect(self.record.setVisible)
            self.body.addWidget(toggle)
            self.body.addWidget(self.record)
