# EasyMeasurement - tests/test_report_language.py
# A protocol in another language than the program, chosen per protocol.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.reporting.context import build_context
from easymeasurement.l10n import tr
from easymeasurement.reporting.language import day, languages, moment, speaking, value_text
from easymeasurement.reporting.nodes import Fields, Heading, Letterhead, SignatureLine
from easymeasurement.reporting.template import default_template_text, parse_template, resolve


def campaign_with_one_value(app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    app.service.add_measurement(
        campaign, "rlo", [ResultValue("rlo", "RLO", Quantity.parse("0.21Ω"), Verdict.PASSED)],
        datetime(2026, 5, 4, 10, 0), Verdict.PASSED,
    )
    return campaign


def texts(app, campaign, code, template=None):
    with speaking(code):
        nodes = resolve(parse_template(template or default_template_text()),
                        build_context(app.service, campaign))
    found = []
    for node in nodes:
        if isinstance(node, Heading):
            found.append(node.text)
        elif isinstance(node, Fields):
            found += [text for row in node.rows for text in row]
        elif isinstance(node, Letterhead):
            found += [node.title, *node.lines, *node.client, *node.contractor]
        elif isinstance(node, SignatureLine):
            found += [node.result, *node.labels]
    return found


def test_english_is_offered_beside_german():
    assert languages()["en"] == "English"
    assert languages()["de"] == "Deutsch"


def test_an_english_protocol_has_english_words(app, asset):
    campaign = campaign_with_one_value(app, asset)
    found = texts(app, campaign, "en")
    assert "Test report" in found
    assert "Time" in found and "Verdict" in found and "passed" in found
    assert "RLO – Protective conductor resistance" in found
    assert "Installation" in found  # the kind of the asset
    assert any(text.startswith("Inspector: ") for text in found)
    assert any(text.startswith("Test result: ") for text in found)


def test_german_stays_as_it_is(app, asset):
    found = texts(app, campaign_with_one_value(app, asset), "de")
    assert "Prüfprotokoll" in found and "bestanden" in found


def test_kinds_and_features_are_translated_by_their_key(app):
    ladder = app.db.add_asset(app.db.add_customer("Muster AG"), "ladder", "Leiter 3 m")
    app.db.set_asset_features(ladder, {"length": "3", "number_of_rungs": "10", "material": ""})
    campaign = campaign_with_one_value(app, ladder)
    found = texts(app, campaign, "en")
    assert "Ladder" in found  # a ladder, not the conductors that share the German word
    assert "Length" in found and "3\u202fm" in found and "Number of rungs" in found
    assert "Material" not in found  # left empty
    spanish = texts(app, campaign, "es")
    assert "Escalera" in spanish and "Número de peldaños" in spanish
    german = texts(app, campaign, "de")
    assert "Leiter" in german and "Sprossenzahl" in german


def test_a_kind_added_in_the_settings_keeps_its_german_name(app):
    from easymeasurement.store.kinds import Feature, Kind
    app.db.save_kind(Kind("pumpe", "Pumpe", features=(Feature("foerderhoehe", "Förderhöhe", "m"),)))
    pump = app.db.add_asset(app.db.add_customer("Muster AG"), "pumpe", "P1")
    app.db.set_asset_features(pump, {"foerderhoehe": "12"})
    found = texts(app, campaign_with_one_value(app, pump), "en")
    assert "Pumpe" in found and "Förderhöhe" in found


def test_what_is_not_translated_stays_as_written():
    with speaking("en"):
        assert tr("Ein Satz, den niemand übersetzt hat") == "Ein Satz, den niemand übersetzt hat"


def test_a_template_can_give_its_own_words_per_language(app, asset):
    template = "blocks:\n  - type: heading\n    text: {de: Abnahme, en: Acceptance}\n"
    campaign = campaign_with_one_value(app, asset)
    assert texts(app, campaign, "en", template) == ["Acceptance"]
    assert texts(app, campaign, "de", template) == ["Abnahme"]


def test_the_language_stays_with_the_protocol_and_its_signed_copy(app, asset, tmp_path):
    from easymeasurement.reporting.sign import Pkcs12Signer

    from .test_report_signing import smime_identity

    campaign = campaign_with_one_value(app, asset)
    app.db.execute("UPDATE campaigns SET driver='profitest-prime' WHERE id=?", campaign)
    app.service.close(campaign)
    report = app.archive.generate(campaign, "Standard", default_template_text(), "en")
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "x")
    app.archive.sign(report, Pkcs12Signer(certificate, "x"))
    assert [r["language"] for r in app.archive.reports(campaign)] == ["en", "en"]


def test_the_language_is_left_after_the_protocol(app, asset):
    campaign = campaign_with_one_value(app, asset)
    app.service.close(campaign)
    app.archive.generate(campaign, "Standard", default_template_text(), "en")
    assert tr("passed") == "bestanden"


def test_a_reading_keeps_its_digits_and_takes_the_decimal_sign_of_the_language():
    with speaking("de"):
        assert value_text("2.05MΩ") == "2,05\u202fMΩ"
        assert value_text(">999MΩ") == ">999\u202fMΩ"
    with speaking("en"):
        assert value_text("2,050MΩ") == "2.050\u202fMΩ"
        assert value_text("i.O.") == "i.O."


def test_dates_follow_the_language():
    when = datetime(2026, 5, 4, 10, 5, 7)
    with speaking("de"):
        assert moment(when, seconds=True) == "04.05.2026 10:05:07"
    with speaking("en"):
        assert day(when) == "2026-05-04"
    with speaking("es"):
        assert moment(when) == "04/05/2026 10:05"


def test_the_same_campaign_in_three_languages(app, asset):
    campaign = campaign_with_one_value(app, asset)
    assert "0,21\u202fΩ" in texts(app, campaign, "de")
    assert "0.21\u202fΩ" in texts(app, campaign, "en")
    spanish = texts(app, campaign, "es")
    assert "Informe de ensayo" in spanish and "0,21\u202fΩ" in spanish and "correcto" in spanish


def test_every_report_language_knows_every_stored_word():
    import yaml

    from easymeasurement.l10n.catalog import STORED, folder

    def stored(code):
        return {text for entry in (folder() / code).iterdir() if entry.name.startswith(STORED)
                for text in yaml.safe_load(entry.read_text("utf-8"))["texts"]}

    words = [stored(code) for code in languages() if code != "en"]
    assert all(found == words[0] for found in words)


def test_a_german_template_reads_in_english(app, asset):
    template = "blocks:\n  - type: heading\n    text: Prüfprotokoll\n"
    campaign = campaign_with_one_value(app, asset)
    assert texts(app, campaign, "en", template) == ["Test report"]
    assert texts(app, campaign, "de", template) == ["Prüfprotokoll"]
