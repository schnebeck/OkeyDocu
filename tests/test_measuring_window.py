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

from okeydocu.devices.guide import LEADS, STATIONS
from okeydocu.devices.profitest_prime.guides import GUIDES, guide_for
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.l10n import speaking
from okeydocu.ui.lead_art import route
from okeydocu.ui.measuring_window import MeasuringWindow
from okeydocu.ui.test_objects import DRAWINGS


@pytest.fixture
def window(qtbot):
    with speaking("de"):
        shown = MeasuringWindow(DRIVER_KEY, "rcd_time", "=K1-F1", ["30 mA · A", "25 A"], 4)
    qtbot.addWidget(shown)
    shown.resize(1440, 1020)
    shown.show()
    return shown


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
    window.bench.show_guide(guide_for("rcd_time"), ["30 mA"], poles, n_left)
    window.go(LEADS)
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
    assert "Anlage" in window.chips[0].text()
    window.next.click()
    window.next.click()
    assert window.station == LEADS
    assert window.bench._lay.state() == window.bench._lay.State.Running
    window.next.click()
    assert window.bench.progress == len(window.guide.leads)
    assert window.chips[LEADS].text().startswith("✓")


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
