# OkeyDocu - tests/test_setting_check.py
# Instrument settings held against the element they were set for.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.plan import load_instructions
from okeydocu.campaign.setting_check import NoRcd, SettingCheck, Unstated, same
from okeydocu.devices import LiveReading
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.profitest_prime.parser import parse_event
from okeydocu.importing.izytron_measurements import _parameter
from okeydocu.l10n import speaking
from okeydocu.ui import step_text
from okeydocu.ui.setting_warning import ORANGE, campaign_note

RCD_PUSH = (
    '<Event xmlns="http://example.org/Common-Event-xml" name="OnSavePressed">'
    '<EventArgs><MEASUREMENT comment="" completed="true"'
    ' guid="aaaaaaaa-0000-1000-8000-000000000001" passed="true"'
    ' testdate="2026-03-01T10:00:00.000" tester="Tester" type="TS1297">'
    '<RANGEDPARAMETER description="TS1228" value="30mA"/>'
    '<RANGEDPARAMETER description="TS1230" value="63A"/>'
    '<TRANSLATEABLEPARAMETER description="TS1238" value="B"/>'
    '<RESULT lowerlimit="&gt;0ms" upperlimit="&lt;300ms" passed="true" value="21ms"'
    ' variable="TS1349"/>'
    "</MEASUREMENT></EventArgs></Event>"
).encode()


@pytest.fixture
def rcd(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    switch = app.db.add_asset(customer, "rcd", "FI Steuerung", machine, identifier="=K1-F1")
    app.db.set_asset_features(switch, {"rcd_type": "A", "rated_current": "25",
                                       "rated_residual_current": "30"})
    circuit = app.db.add_asset(customer, "circuit", "Steckdosen", switch)
    return {"machine": machine, "switch": switch, "circuit": circuit}


def test_settings_are_compared_in_base_units_and_by_their_last_word():
    assert same("30mA", "30 mA") is True
    assert same("63 A", "25 A") is False
    assert same("Typ B", "B") is True
    assert same("B", "A") is False
    assert same("A - EV", "A-EV") is True
    assert same("A - EV", "A") is False
    assert same("B+", "B") is False
    assert same("63 A", "A") is None
    assert same("", "A") is None


def test_the_instruments_codes_become_keys_of_the_vocabulary():
    parameters = dict((p.key, p.value) for p in parse_event(RCD_PUSH).parameters)
    assert parameters == {"rated_residual_current": "30mA", "rated_current": "63A",
                          "rcd_type": "B"}
    imported = _parameter({"Name": "RCD - Typ", "Value": "B", "TsKey": "PROFITEST_TS1238"})
    assert (imported.key, imported.value) == ("rcd_type", "B")


def test_the_rcd_above_the_measured_element_decides(app, rcd):
    check = SettingCheck(app.db)
    assert check.expected(rcd["circuit"]) == [("rcd_type", "A"),
                                              ("rated_residual_current", "30 mA"),
                                              ("rated_current", "25 A")]
    assert check.element(rcd["circuit"]) == "=K1-F1"
    assert check.expected(rcd["machine"]) == []
    found = check.findings("rcd_time", [("rcd_type", "B"), ("rated_current", "63A"),
                                        ("rated_residual_current", "30mA")], rcd["circuit"])
    assert [(m.key, m.used, m.expected) for m in found] == [("rcd_type", "B", "A"),
                                                           ("rated_current", "63A", "25 A")]


def test_a_code_is_judged_by_the_instruments_own_word(app, rcd):
    app.db.save_device_texts(DRIVER_KEY, "1.0", "1", {"de-DE": {"TS1463": "B"},
                                                      "en-GB": {"TS1463": "B"}})
    with speaking("de"):
        found = SettingCheck(app.db).findings("rcd_time", [("rcd_type", "TS1463")],
                                              rcd["circuit"])
    assert [(m.used, m.expected) for m in found] == [("B", "A")]


def test_a_code_without_words_is_not_judged(app, rcd):
    found = SettingCheck(app.db).findings("rcd_time", [("rcd_type", "TS9999")], rcd["circuit"])
    assert found == []


def test_a_setting_the_rcd_does_not_state_is_named_instead_of_judged(app, rcd):
    app.db.set_asset_features(rcd["switch"], {"rcd_type": "B"})
    parameters = [("rcd_type", "B"), ("rated_current", "63 A")]
    found = SettingCheck(app.db).findings("rcd_time", parameters, rcd["circuit"])
    assert found == [Unstated(("rated_residual_current", "rated_current"), "=K1-F1")]


def test_an_rcd_test_without_an_rcd_above_is_a_finding(app, rcd):
    found = SettingCheck(app.db).findings("rcd_time", [("rcd_type", "B")], rcd["machine"])
    assert found == [NoRcd()]


def test_only_rcd_tests_are_held_against_the_rcd(app, rcd):
    check = SettingCheck(app.db)
    assert check.findings("zloop", [("rated_current", "16 A")], rcd["circuit"]) == []
    assert check.findings("zloop", [], rcd["machine"]) == []


def test_the_instruction_names_the_settings_of_the_chosen_element(app, rcd):
    step = load_instructions()["rcd_time"]
    check = SettingCheck(app.db)
    with speaking("de"):
        chosen = step_text.settings_html(step, check.expected(rcd["circuit"]), "=K1-F1")
        plain = step_text.settings_html(step)
    assert "Am Gerät einstellen für =K1-F1" in chosen
    assert "RCD-Typ: <b>A</b>" in chosen and "Nennstrom: <b>25 A</b>" in chosen
    assert "RCD-Typ: <b>laut Typenschild</b>" in plain


def test_a_differing_push_warns_at_once_and_stays_orange(window, app, rcd):
    campaign = app.service.create(rcd["machine"], "Prüfung", "Tester")
    page = window.campaign
    page.show_campaign(campaign)
    page.place_targets[campaign] = rcd["circuit"]
    page._received(campaign, LiveReading(parse_event(RCD_PUSH), datetime(2026, 3, 1, 10, 0, 5)))
    assert page.settings_warning is not None and page.settings_warning.isVisible()
    page.settings_warning.accept()
    page.values.show_point(None)
    table = page.values.table
    assert table.item(0, 0).background().color() == ORANGE
    assert "=K1-F1" in table.item(0, 0).toolTip()
    with speaking("de"):
        assert "1 RCD-Test passt nicht zu seinem RCD" in campaign_note(app.db, campaign)


def test_a_matching_push_raises_no_warning(window, app, rcd):
    app.db.set_asset_features(rcd["switch"], {"rcd_type": "B", "rated_current": "63",
                                              "rated_residual_current": "30"})
    campaign = app.service.create(rcd["machine"], "Prüfung", "Tester")
    page = window.campaign
    page.show_campaign(campaign)
    page.place_targets[campaign] = rcd["circuit"]
    page._received(campaign, LiveReading(parse_event(RCD_PUSH), datetime(2026, 3, 1, 10, 0, 5)))
    assert page.settings_warning is None
    assert campaign_note(app.db, campaign) == ""


def test_an_rcd_test_on_a_place_without_rcd_warns_in_a_window(window, app, rcd):
    campaign = app.service.create(rcd["machine"], "Prüfung", "Tester")
    page = window.campaign
    page.show_campaign(campaign)
    page._received(campaign, LiveReading(parse_event(RCD_PUSH), datetime(2026, 3, 1, 10, 0, 5)))
    warning = page.settings_warning
    assert warning.isVisible() and warning.icon() == warning.Icon.Warning
    assert "Nicht an einem RCD gebucht" in warning.text()
    warning.accept()


def test_the_guide_asks_for_the_rcd_when_none_is_chosen(app, rcd):
    step = load_instructions()["rcd_time"]
    with speaking("de"):
        missing = step_text.settings_html(step, [], None)
        unstated = step_text.settings_html(step, [("rcd_type", "A")], "=K1-F1")
    assert "Kein RCD gewählt" in missing
    assert "bei =K1-F1 eintragen" in unstated
