# EasyMeasurement - tests/test_repeat.py
# A repeat inspection: the last one's measurements as points, filled in any order.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.model import MeterMeasurement, Parameter, Quantity, ResultValue, Verdict


def _riso(text, lower=">1.00MΩ"):
    return ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, lower, "")


def _reading(uid, conductor, voltage="500 V", lower=">1.00MΩ", text="20MΩ"):
    return MeterMeasurement(
        uid=uid, function="riso", taken_at=datetime(2026, 5, 4, 9), verdict=Verdict.PASSED,
        results=(_riso(text, lower),),
        parameters=(Parameter("RISO - Nennspannung", voltage),
                    Parameter("RISO - Leiter", conductor)),
    )


@pytest.fixture
def last(app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    first = app.service.create(press, "Erstprüfung", "Prüfer")
    for uid, conductor in (("a", "L1-PE"), ("b", "L2-PE")):
        measurement = app.service.insert_imported(
            first, _reading(uid, conductor), "import:test", datetime(2025, 5, 4, 9), None, None,
            None, cabinet)
        app.db.execute("UPDATE measurements SET hint=? WHERE id=?", f"Klemme {uid} lösen",
                       measurement)
    run = app.service.add_run(first, "Sichtprüfung der Betriebsmittel", "Sichtprüfung",
                              datetime(2025, 5, 4, 8))
    values = [ResultValue("question", "Prüffrage", Quantity(raw="Ist der Schrank zugänglich?")),
              ResultValue("answer", "Antwort", Quantity(raw="yes")),
              ResultValue("note", "Bemerkung", Quantity(raw="nur mit Schlüssel"))]
    check = app.service.add_measurement(first, "visual_inspection", values,
                                        datetime(2025, 5, 4, 8), Verdict.PASSED, asset_id=cabinet)
    app.service.join_run(check, run, "Zugänglichkeit")
    app.service.close(first)
    again = app.service.create(press, "Wiederholung", "Prüfer")
    app.service.make_repeat(again, app.service.last_closed(press)["id"])
    return {"first": first, "again": again, "press": press, "cabinet": cabinet}


def _points(app, campaign):
    return {step.title + "/" + dict(step.parameters).get("RISO - Leiter", ""): (row, step)
            for row, step in app.service.points(campaign)}


def test_the_last_inspection_becomes_a_list_of_points(app, last):
    points = _points(app, last["again"])
    assert set(points) == {"RISO/L1-PE", "RISO/L2-PE", "Zugänglichkeit/"}
    _, riso = points["RISO/L1-PE"]
    assert riso.asset_id == last["cabinet"]
    assert riso.limits == (("riso", "RISO", ">1.00MΩ", ""),)
    assert riso.hint == "Klemme a lösen"
    _, check = points["Zugänglichkeit/"]
    assert (check.kind, check.question, check.remark) == (
        "check", "Ist der Schrank zugänglich?", "nur mit Schlüssel")
    assert app.service.blockers(last["again"])[0].startswith("3 Punkte der Wiederholung offen")


def test_a_reading_takes_the_point_of_its_element_and_conductor(app, last):
    taken = app.service.insert_imported(last["again"], _reading("n2", "L2-PE"), "device:x",
                                        datetime(2026, 5, 4, 9), None, None, None,
                                        last["cabinet"])
    row, step = _points(app, last["again"])["RISO/L2-PE"]
    assert app.db.one("SELECT step_id, hint FROM measurements WHERE id=?", taken)[:] == (
        row["id"], "Klemme b lösen")
    assert _points(app, last["again"])["RISO/L2-PE"][0]["status"] == "done"
    assert _points(app, last["again"])["RISO/L1-PE"][0]["status"] == "pending"


def test_a_reading_elsewhere_leaves_the_point_open(app, last):
    taken = app.service.insert_imported(last["again"], _reading("n1", "L1-PE"), "device:x",
                                        datetime(2026, 5, 4, 9), None, None, None, last["press"])
    assert app.db.one("SELECT step_id FROM measurements WHERE id=?", taken)[0] is None
    app.service.move_measurements([taken], last["cabinet"])
    assert app.db.one("SELECT step_id FROM measurements WHERE id=?", taken)[0] is not None
    app.service.move_measurements([taken], last["press"])
    row, _ = _points(app, last["again"])["RISO/L1-PE"]
    assert row["status"] == "pending"


def test_other_limits_or_settings_need_a_reason(app, last):
    app.service.insert_imported(last["again"], _reading("n1", "L1-PE", "250 V", ">0.50MΩ"),
                                "device:x", datetime(2026, 5, 4, 9), None, None, None,
                                last["cabinet"])
    row, step = _points(app, last["again"])["RISO/L1-PE"]
    taken = app.service.point_measurement(row["id"])
    assert app.service.deviations(step, taken["id"]) == [
        "Grenze RISO: >0.50MΩ statt >1.00MΩ", "RISO - Nennspannung: 250 V statt 500 V"]
    assert any("Abweichende Einstellung" in p for p in app.service.blockers(last["again"]))
    app.service.accept_deviation(row["id"], "Frequenzumrichter verträgt nur 250 V")
    assert not any("Abweichende" in p for p in app.service.blockers(last["again"]))


def test_the_same_limit_written_otherwise_is_no_deviation(app, last):
    app.service.insert_imported(last["again"], _reading("n1", "L1-PE", lower="> 1,00 MΩ"),
                                "device:x", datetime(2026, 5, 4, 9), None, None, None,
                                last["cabinet"])
    row, step = _points(app, last["again"])["RISO/L1-PE"]
    assert app.service.deviations(step, app.service.point_measurement(row["id"])["id"]) == []


def test_skipped_with_a_reason_and_answered_the_campaign_can_close(app, last):
    points = _points(app, last["again"])
    for key in ("RISO/L1-PE", "RISO/L2-PE"):
        app.service.skip_step(points[key][0]["id"], "Anlage außer Betrieb")
    app.service.answer_step(points["Zugänglichkeit/"][0]["id"], "yes", "wieder nur mit Schlüssel")
    assert app.service.blockers(last["again"]) == []
    answer = app.db.one("SELECT * FROM measurements WHERE campaign_id=? AND function=?",
                        last["again"], "visual_inspection")
    assert answer["step_name"] == "Zugänglichkeit" and answer["asset_id"] == last["cabinet"]
    assert app.service.run(answer["run_id"])["name"] == "Sichtprüfung der Betriebsmittel"
    question = app.db.one("SELECT raw FROM measured_values WHERE measurement_id=? AND key=?",
                          answer["id"], "question")[0]
    assert question == "Ist der Schrank zugänglich?"
    app.service.close(last["again"])


def test_last_values_come_back_for_comparison(app, last):
    app.service.insert_imported(last["again"], _reading("n1", "L1-PE", text="5MΩ"), "device:x",
                                datetime(2026, 5, 4, 9), None, None, None, last["cabinet"])
    row, step = _points(app, last["again"])["RISO/L1-PE"]
    line, notable = app.service.comparison(step, app.service.point_measurement(row["id"])["id"])
    assert "RISO 20MΩ" in line and notable == ["RISO deutlich niedriger als zuletzt"]


def test_the_report_groups_a_repeat_by_measurement_and_names_what_was_left_out(app, last):
    from easymeasurement.reporting.context import build_context
    from easymeasurement.reporting.nodes import plain
    points = _points(app, last["again"])
    app.service.insert_imported(last["again"], _reading("n1", "L1-PE"), "device:x",
                                datetime(2026, 5, 4, 9), None, None, None, last["cabinet"])
    app.service.skip_step(points["RISO/L2-PE"][0]["id"], "Anlage außer Betrieb")
    app.service.answer_step(points["Zugänglichkeit/"][0]["id"], "yes")
    steps = build_context(app.service, last["again"])["steps"]
    shown = [(plain(s.title), s.status, s.note, len(s.measurements)) for s in steps]
    assert ("Sichtprüfung der Betriebsmittel", "done", "", 1) in shown
    assert ("RISO · Presse / Schrank · L2-PE", "skipped", "Anlage außer Betrieb", 0) in shown
    assert ("RISO – Isolationswiderstand", "done", "", 1) in shown
    assert len(shown) == 3
