# EasyMeasurement - tests/test_choice_lists.py
# Choice lists live in tables of their own; a value tells what sets it apart from the others.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

from easymeasurement.l10n import speaking
from easymeasurement.store.choice_lists import ChoiceList, ChoiceValue, Method
from easymeasurement.ui.choice_box import ChoiceBox
from easymeasurement.ui.choice_tips import required_time


def test_a_fresh_database_knows_the_shipped_lists_and_the_features_offer_them(app):
    lists = app.db.choice_lists()
    assert lists["characteristic"].entry("gL/gG <0.4s").facts["Disconnection time"] == \
        "at most 0.4 s"
    machine = app.db.kind("machine")
    offered = {feature.key: feature.choice_list for feature in machine.features}
    assert offered["supply_cable"] == "cable_type" and offered["characteristic"] == "characteristic"
    assert app.db.choice_list_usage("cable_type") >= 5


def test_a_list_is_stored_with_its_values_facts_and_methods(app):
    own = ChoiceList("fuse_kind", "Fuse kind", "Which fuse.", ("Breaking",), (
        ChoiceValue("NH", {"Breaking": "high"}, "Blade fuse.", "", b"\x89PNG",
                    (Method("zloop", "as for gG"),)),
        ChoiceValue("D0", {"Breaking": "high"})))
    app.db.save_choice_list(own)
    assert app.db.choice_list("fuse_kind") == own
    app.db.save_choice_list(replace(own, values=own.values[1:]))
    assert app.db.choice_list("fuse_kind").offered == ("D0",)
    count = app.db.one("SELECT count(*) AS n FROM choice_methods")["n"]
    assert count == sum(len(v.methods) for l in app.db.choice_lists().values() for v in l.values)


def test_a_deleted_list_leaves_its_features_as_plain_text(app):
    app.db.delete_choice_list("cable_type")
    machine = app.db.kind("machine")
    assert next(f for f in machine.features if f.key == "supply_cable").choice_list is None


def test_only_what_the_offered_values_do_not_share_is_told(app):
    lists = app.db.choice_lists()
    assert lists["breaker_characteristic"].telling() == (
        "Instantaneous trip", "Disconnecting current Iₐ", "Disconnection time", "Use")
    assert "Protective device" in lists["characteristic"].telling()


def test_the_field_tells_the_value_it_holds_with_its_curve(qtbot, app):
    lists = app.db.choice_lists()
    with speaking("de"):
        box = ChoiceBox(lists["characteristic"], "gL/gG <0,4s")
        qtbot.addWidget(box)
        tip = box.tip(box.currentText())
        assert ("Abschaltzeit", "höchstens 0,4 s") in tip.rows and not tip.pictures
        tip = box.tip("C")
        assert ("Schutzeinrichtung", "Leitungsschutzschalter") in tip.rows
        assert len(tip.pictures) == 1 and tip.lines_title == "Geeignete Messungen"
        assert box.tip("NH 63") is None
        assert box.tip("").title == "Charakteristik"


def test_the_disconnection_time_follows_the_element():
    assert required_time({}) == 0.4
    assert required_time({"earthing_system_type": "TT", "rated_current": "16"}) == 0.2
    assert required_time({"earthing_system_type": "TN-S", "rated_current": "80"}) == 5.0


def test_the_page_stores_an_edited_cell_and_keeps_shipped_texts_english(qtbot, app):
    from easymeasurement.ui.choice_lists_page import ChoiceListsPage
    with speaking("de"):
        page = ChoiceListsPage(app)
        qtbot.addWidget(page)
        page.refresh(select="rcd_type")
        table = page.table.table
        assert table.horizontalHeaderItem(1).text() == "Erfasst"
        table.item(0, 2).setText("50 Hz und 60 Hz")
    stored = app.db.choice_list("rcd_type")
    assert stored.entry("AC").facts["Frequencies"] == "50 Hz und 60 Hz"
    assert stored.entry("AC").facts["Detects"] == "sinusoidal AC residual currents"
    assert stored.attributes == ("Detects", "Frequencies")


def test_the_value_form_hands_on_help_and_methods(qtbot, app):
    from easymeasurement.ui.choice_lists_page import ChoiceListsPage
    page = ChoiceListsPage(app)
    qtbot.addWidget(page)
    page.refresh(select="protection_class")
    page.table.table.setCurrentCell(1, 0)
    page.value_form.help.setPlainText("Two layers of insulation.")
    entry = app.db.choice_list("protection_class").entry("II")
    assert entry.help == "Two layers of insulation." and entry.methods[0].function == "riso"


def test_a_tip_shown_again_holds_only_its_own_content(qtbot):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QLabel

    from easymeasurement.ui import rich_tip
    first = rich_tip.show_tip(rich_tip.Tip("First", text="One\n\nTwo", lines=("a",)), QPoint())
    second = rich_tip.show_tip(rich_tip.Tip("Second"), QPoint())
    assert not first.isVisible() and second.isVisible()
    shown = second.findChildren(QLabel)
    assert len(shown) == 1 and "Second" in shown[0].text()
    assert second.height() >= shown[0].sizeHint().height()
    rich_tip.hide_tip()


def test_every_list_the_shipped_kinds_name_is_shipped():
    from easymeasurement.store.choice_lists import shipped_choice_lists
    from easymeasurement.store.kinds import shipped_kinds
    named = {feature.choice_list for kind in shipped_kinds() for feature in kind.features}
    assert named - {None} <= {found.key for found in shipped_choice_lists()}


def test_f1_in_the_field_sets_all_values_side_by_side(qtbot, app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    from easymeasurement.ui import rich_tip
    from easymeasurement.ui.choice_tips import compare_tip
    lists = app.db.choice_lists()
    tip = compare_tip(lists["rcd_type"], "B")
    heads, *body = tip.grid
    assert len(heads) == 3 and len(body) == len(lists["rcd_type"].values)
    assert body[tip.marked][0] == "B"
    assert compare_tip(lists["cross_section"]) is None
    with speaking("de"):
        box = ChoiceBox(lists["rcd_type"], "F")
        qtbot.addWidget(box)
        box.show()
        assert box.tip("F").hint == "F1 vergleicht alle Werte der Liste."
        qtbot.keyClick(box.lineEdit(), Qt.Key.Key_F1)
        assert rich_tip.showing()
        shown = " ".join(label.text() for label in rich_tip._window.findChildren(QLabel))
        assert "Erfasst" in shown and "font-weight:bold'>F<" in shown
    rich_tip.hide_tip()
