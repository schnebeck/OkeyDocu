# OkeyDocu - tests/test_measuring_window.py
# The guided first measurement: stations, test leads laid one by one, test points drawn.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QImage, QPainter, QPainterPathStroker

from okeydocu.devices.guide import DIAL, LEADS, STATIONS
from okeydocu.devices.profitest_prime.guides import GUIDES, guide_for
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.l10n import speaking
from okeydocu.ui.lead_art import route
from okeydocu.ui.measuring_window import MeasuringWindow
from okeydocu.ui.place_form import NEW
from okeydocu.ui.test_objects import DRAWINGS


@pytest.fixture
def plant(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "construction_distributor", "Schrank", machine,
                               identifier="=K1")
    switch = app.db.add_asset(customer, "rcd", "FI Steuerung", cabinet, identifier="=K1-F1")
    other = app.db.add_asset(customer, "rcd", "FI Licht", cabinet, identifier="=K1-F2")
    app.db.set_asset_features(switch, {"rcd_type": "A", "rated_residual_current": "30",
                                       "rated_current": "25", "number_of_poles": "4"})
    circuit = app.db.add_asset(customer, "circuit", "Steckdosen", switch)
    campaign = app.service.create(machine, "Prüfung", "Tester")
    return {"campaign": campaign, "machine": machine, "switch": switch, "other": other,
            "circuit": circuit}


def opened(qtbot, app, plant, asset_id):
    with speaking("de"):
        shown = MeasuringWindow(app, plant["campaign"], DRIVER_KEY, "rcd_time", asset_id)
    qtbot.addWidget(shown)
    shown.resize(1440, 1020)
    shown.show()
    return shown


@pytest.fixture
def window(qtbot, app, plant):
    return opened(qtbot, app, plant, plant["circuit"])


def anchors_of(test_object: str, poles: int, n_left: bool) -> dict:
    image = QImage(1000, 260, QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    try:
        return DRAWINGS[test_object](painter, QRectF(0, 0, 1000, 250), ["30 mA"], poles, n_left)
    finally:
        painter.end()


def test_every_lead_of_a_guide_has_its_row_and_its_terminal(window):
    for guide in GUIDES.values():
        for poles, n_left in ((2, False), (4, False), (4, True)):
            anchors = anchors_of(guide.test_object, poles, n_left)
            assert {lead.terminal for lead in guide.leads} <= set(anchors)
        assert all(window.bench.panel.front.elementExists(lead.row) for lead in guide.leads)


@pytest.mark.parametrize("n_left, order", [(False, ("out_l", "out_n")), (True, ("out_n", "out_l"))])
def test_n_stands_after_the_line_conductors_or_first(n_left, order):
    anchors = anchors_of("rcd", 4, n_left)
    left, right = (anchors[key].point.x() for key in order)
    assert left < right
    assert abs(right - left) == 40 if n_left else abs(right - left) == 120


@pytest.mark.parametrize("poles, n_left, crossing", [
    (2, False, {"1", "2"}), (4, False, {"1", "2"}), (4, True, None)])
def test_leads_cross_only_where_plugs_and_terminals_force_it(window, poles, n_left, crossing):
    """Plugs stacked L over N, terminals side by side L before N: one bridge is unavoidable.
    With N first on the RCD the orders agree and nothing crosses; PE never crosses."""
    window.go(LEADS)
    window.bench.show_guide(guide_for("rcd_time"), ["30 mA"], poles, n_left)
    window.bench.finish()
    window.bench.repaint()
    bench = window.bench
    field = bench.panel.part_rect("socket-1").left()
    stroker = QPainterPathStroker()
    stroker.setWidth(2)
    below = sorted((lead for lead in bench.guide.leads if bench.anchors[lead.terminal].side > 0),
                   key=lambda lead: bench.anchors[lead.terminal].point.x())
    rows = sorted({lead.row for lead in bench.guide.leads})
    outlines = {}
    for lead in bench.guide.leads:
        anchor = bench.anchors[lead.terminal]
        row = bench.panel.part_rect(lead.row)
        lane = field - 28 * (len(rows) - rows.index(lead.row))
        depth = 18 + 16 * below.index(lead) if lead in below else 34
        outlines[lead.plug] = stroker.createStroke(
            route(QPointF(row.left(), row.center().y()), lane, anchor, depth))
    plugs = sorted(outlines)
    crossed = [{a, b} for i, a in enumerate(plugs) for b in plugs[i + 1:]
               if outlines[a].intersects(outlines[b])]
    assert crossed == ([crossing] if crossing else [])


def test_the_window_opens_on_the_first_station_and_goes_on_without_waiting(window):
    assert window.station == 0 and not window.back.isEnabled()
    assert "Anlage" in window.bar.chips[0].text()
    window.next.click()
    window.next.click()
    assert window.station == LEADS
    assert window.bench._lay.state() == window.bench._lay.State.Running
    window.next.click()
    assert window.bench.progress == len(window.guide.leads)
    assert window.bar.chips[LEADS].text().startswith("✓")


def test_the_leads_station_names_every_probe_in_order(window):
    with speaking("de"):
        window.go(LEADS)
        text = window.step_text.text()
    assert "Die Kabel 1, 2, 3 stecken in ihren Buchsenreihen." in text
    assert text.index("PE (L2)") < text.index("L (L1)") < text.index("N (L3)")
    assert "Verbraucher vorher sichern" in text
    assert window.next.text() == "Angeschlossen – weiter ▶"


def test_laying_lights_up_the_rows_of_the_leads_laid_so_far(window):
    window.go(LEADS)
    window.bench._laid(1.2)
    assert window.bench.panel.pointed == ("socket-3", "socket-1")
    assert window.bench.panel.target == 18


def test_the_last_station_closes_the_window(window):
    window.go(len(STATIONS) - 1)
    window.next.click()
    assert window.result() == window.DialogCode.Accepted


# Station "Installation" ------------------------------------------------------------------


def test_the_rcd_above_the_chosen_place_is_the_test_point(window, plant):
    assert window.place.asset_id == plant["switch"]
    assert window.place.path == ("Presse", "Schrank =K1")
    assert window.place.lines() == ["30 mA · A", "25 A"] and window.place.poles == 4
    assert window.form.choice.currentData() == plant["switch"]
    assert window.form.choice.count() == 3
    assert window.form.choice.itemData(2) == NEW


def test_a_missing_detail_is_marked_and_does_not_stop_the_tester(window):
    field = window.form.fields["n_terminal"]
    assert "fde2c4" in field.styleSheet()
    assert "Fehlende Angaben" in window.form.hint.text()
    window.next.click()
    assert window.station == 1


def test_what_is_entered_is_stored_at_the_element_as_the_list_holds_it(window, app, plant):
    window.form.fields["n_terminal"].setEditText("links")
    window.next.click()
    assert app.db.asset_features(plant["switch"])["n_terminal"] == "left"
    assert window.place.n_left and window.bench.n_left


def test_another_element_can_be_chosen(window, plant):
    window.form.choice.setCurrentIndex(window.form.choice.findData(plant["other"]))
    window.form.choice.activated.emit(window.form.choice.currentIndex())
    assert window.place.asset_id == plant["other"]
    assert window.place.lines() == ["? mA", "? A"]


def test_without_an_rcd_the_station_makes_one_on_the_way(qtbot, app, plant):
    window = opened(qtbot, app, plant, plant["machine"])
    made = []
    window.place_made.connect(made.append)
    assert window.place.is_new and window.form.choice.currentData() == NEW
    window.form.identifier.setText("=K2-F1")
    window.form.fields["rcd_type"].setEditText("B")
    window.form.fields["rated_residual_current"].setEditText("300")
    window.next.click()
    element = app.db.asset(made[0])
    assert (element["identifier"], element["name"], element["parent_id"]) == \
        ("=K2-F1", "RCD", plant["machine"])
    assert app.db.asset_features(made[0]) == {"rcd_type": "B", "rated_residual_current": "300"}
    assert window.place.asset_id == made[0] and not window.place.is_new


def test_a_new_element_hangs_where_it_was_put_and_that_place_is_kept(qtbot, app, plant):
    window = opened(qtbot, app, plant, plant["machine"])
    kept = []
    window.parent_chosen.connect(kept.append)
    window.form.fields["rcd_type"].setEditText("A")
    box = window.form.parent_box
    box.setCurrentIndex(box.findData(plant["switch"]))
    box.activated.emit(box.currentIndex())
    assert kept == [plant["switch"]]
    assert window.place.path[-1] == "FI Steuerung =K1-F1"
    assert window.form.entered()["rcd_type"] == "A"
    again = opened(qtbot, app, plant, plant["machine"])
    assert again.parent_id == plant["machine"]
    with speaking("de"):
        chosen = MeasuringWindow(app, plant["campaign"], DRIVER_KEY, "rcd_time",
                                 plant["machine"], new_parent=plant["switch"])
    qtbot.addWidget(chosen)
    assert chosen.parent_id == plant["switch"]


def test_a_detail_loses_its_mark_once_entered(qtbot, app, plant):
    window = opened(qtbot, app, plant, plant["machine"])
    field = window.form.fields["rated_current"]
    assert "fde2c4" in field.styleSheet()
    field.setEditText("40")
    assert field.styleSheet() == ""
    assert "40 A" in window._shown().lines()


# Station "Rotary switch" -------------------------------------------------------------------


@pytest.mark.parametrize("value, right", [(18, True), (19, True), (17, False), (13, False)])
def test_a_position_that_also_measures_the_function_counts_as_right(value, right):
    from okeydocu.devices.profitest_prime.selector import selector_position
    from okeydocu.ui.station_texts import fits

    assert fits(guide_for("rcd_time"), selector_position(value)) is right
    assert selector_position(value).value == value


def test_the_dial_station_zooms_in_and_goes_on_once_the_switch_is_right(window, qtbot):
    from okeydocu.devices.profitest_prime.selector import selector_position

    window.go(DIAL)
    qtbot.waitUntil(lambda: window.bench.panel.view.width() < 400, timeout=3000)
    assert window.bench.panel.pointed == ("pos-18",)
    window.show_selector(selector_position(17))
    assert "Das Messgerät steht auf" in window.step_text.text()
    assert window.bench.panel.actual == 17 and window.bench.panel.fits is False
    qtbot.wait(1200)
    assert window.station == DIAL
    window.show_selector(selector_position(18))
    assert "steht richtig" in window.step_text.text()
    qtbot.waitUntil(lambda: window.station == LEADS, timeout=3000)
    qtbot.waitUntil(lambda: window.bench.panel.view.width() > 1000, timeout=3000)


def test_without_an_instrument_the_dial_station_waits_for_the_tester(window):
    window.go(DIAL)
    assert "Kein Messgerät verbunden" in window.step_text.text()
    assert window.next.text() == "Gedreht – weiter ▶"
    window.next.click()
    assert window.station == LEADS
