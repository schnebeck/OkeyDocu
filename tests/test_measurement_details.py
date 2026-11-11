# EasyMeasurement - tests/test_measurement_details.py
# A right click on a measurement shows what was measured how, and every figure's role.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

from easymeasurement.devices.base import LiveReading
from easymeasurement.devices.profitest_prime.parser import parse_event
from easymeasurement.l10n import speaking
from easymeasurement.ui.measurement_details import (
    MeasurementDetails,
    details_html,
    readable_record,
)

# An invented push of an RLO measurement that passed, with both polarities and the offset.
RLO_PUSH = (
    '<Event xmlns="http://www.gossenmetrawatt.com/Common-Event-xml" name="OnSavePressed">'
    "<EventArgs><MEASUREMENT comment=\"Clamp on the door hinge\" completed=\"true\""
    ' guid="11111111-2222-3333-4444-555555555555" passed="true"'
    ' testdate="2026-03-01T10:00:00.000" tester="Tester" type="TS1285">'
    '<TRANSLATEABLEPARAMETER description="TS1252" value="TS1253"/>'
    '<RESULT lowerlimit="" upperlimit="&lt;1.00Ω" passed="true" value="0.21Ω" variable="TS1358"/>'
    '<RESULT upperlimit="&lt;1.00Ω" passed="true" value="0.21Ω" variable="TS1360"/>'
    '<RESULT upperlimit="&lt;1.00Ω" passed="true" value="0.19Ω" variable="TS1361"/>'
    '<RESULT passed="false" value="0.04Ω" variable="TS1362"/>'
    "</MEASUREMENT></EventArgs></Event>"
).encode()


def pushed(app, asset):
    campaign = app.service.create(asset, "Inspection", "Tester")
    reading = LiveReading(parse_event(RLO_PUSH), datetime(2026, 3, 1, 10, 0, 5))
    return app.service.receive(campaign, reading)


def test_every_figure_says_what_it_stands_for(app, asset):
    row = app.db.one("SELECT * FROM measurements WHERE id=?", pushed(app, asset))
    with speaking("en"):
        html = details_html(app, row)
    assert "<i>R</i><sub rise='30%'>LO</sub>" in html
    assert "Measuring condition" in html
    assert "Only if not passed</td><td style='padding-right:14px'>no" in html
    assert "220 mΩ" not in html and "210 mΩ" in html
    assert "Clamp on the door hinge" in html


def test_the_view_speaks_german(app, asset):
    row = app.db.one("SELECT * FROM measurements WHERE id=?", pushed(app, asset))
    with speaking("de"):
        html = details_html(app, row)
    assert "Messbedingung" in html and "Schutzleiterwiderstand" in html


def test_the_instruments_record_is_laid_out_in_lines():
    assert readable_record("<a><b x='1'/></a>").splitlines()[1:3] == ["<a>", "  <b x=\"1\"/>"]
    assert readable_record('{"a": [1]}') == '{\n  "a": [\n    1\n  ]\n}'
    assert readable_record("not a record") == "not a record"


def test_the_view_opens_over_the_window(qtbot, app, asset):
    measurement = pushed(app, asset)
    view = MeasurementDetails(app, measurement)
    qtbot.addWidget(view)
    assert "<sub rise='30%'>LO</sub>" in view.text.text()
    assert "TS1285" in view.record.toPlainText()
