# OkeyDocu - tests/test_company.py
# The own firm, entered once and shown in the letterhead of every report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io

from PIL import Image

from okeydocu.reporting.context import build_context
from okeydocu.reporting.logo import prepare_logo
from okeydocu.reporting.nodes import Letterhead
from okeydocu.reporting.pdf import render_pdf
from okeydocu.reporting.template import default_template_text, parse_template, resolve
from okeydocu.ui.company_form import CompanyForm


def _logo_file(tmp_path):
    path = tmp_path / "logo.png"
    Image.new("RGBA", (400, 120), (20, 90, 160, 255)).save(path)
    return path


def _letterhead(app, campaign, template=None):
    nodes = resolve(parse_template(template or default_template_text()),
                    build_context(app.service, campaign))
    return next(node for node in nodes if isinstance(node, Letterhead))


def test_the_firm_is_empty_until_entered_and_keeps_what_was_saved(app):
    assert app.db.company()["name"] == ""
    app.db.save_company(name="Prüfdienst GmbH", city="Hannover")
    app.db.save_company(zip="30159")
    assert app.db.company() | {"logo": ""} == {
        "name": "Prüfdienst GmbH", "street": "", "zip": "30159", "city": "Hannover",
        "phone": "", "email": "", "web": "", "logo": ""}


def test_the_form_keeps_its_entries_only_on_taking_them_over(app, window, tmp_path):
    form = CompanyForm(app, window)
    form.fields["name"].setText("Prüfdienst GmbH")
    form.fields["city"].setText("Hannover")
    assert form.take_logo(_logo_file(tmp_path)) and form.remove_button.isEnabled()
    form.reject()
    assert app.db.company()["name"] == ""
    form = CompanyForm(app, window)
    form.fields["name"].setText("  Prüfdienst GmbH ")
    form.take_logo(_logo_file(tmp_path))
    form.accept()
    stored = app.db.company()
    assert stored["name"] == "Prüfdienst GmbH" and stored["logo"]
    assert CompanyForm(app, window).choose_button.text() == "Ersetzen …"


def test_an_unreadable_logo_is_refused_with_a_reason(app, window, tmp_path):
    broken = tmp_path / "kaputt.png"
    broken.write_bytes(b"no picture")
    form = CompanyForm(app, window)
    assert not form.take_logo(broken) and form.hint.text()


def test_the_letterhead_names_the_firm_and_carries_its_logo(app, asset, tmp_path):
    campaign = app.service.create(asset, "Prüfung", "Anna Prüfer")
    head = _letterhead(app, campaign)
    assert head.contractor == ["Prüfer: Anna Prüfer"] and head.logo is None  # nothing entered
    _, logo = prepare_logo(_logo_file(tmp_path).read_bytes())
    app.db.save_company(name="Prüfdienst GmbH", street="Am Prüffeld 1", zip="30159",
                        city="Hannover", logo=logo)
    head = _letterhead(app, campaign)
    assert head.contractor == ["Prüfdienst GmbH", "Am Prüffeld 1", "30159 Hannover",
                               "Prüfer: Anna Prüfer"]
    assert head.logo.startswith(b"\x89PNG")
    stream = io.BytesIO()
    render_pdf([head], stream)
    assert stream.getvalue().startswith(b"%PDF")
    without = default_template_text().replace("    logo: true\n", "    logo: false\n")
    assert _letterhead(app, campaign, without).logo is None


def test_the_firm_is_found_under_settings(window):
    from PySide6.QtWidgets import QMenu
    menu = next(m for m in window.menuBar().findChildren(QMenu) if m.title() == "&Einstellungen")
    assert menu.actions()[0] is window.company_action and window.company_action.text() == "Firma …"


def test_taking_the_firm_over_redraws_the_template_preview(window, monkeypatch):
    drawn = []
    monkeypatch.setattr(window.templates, "preview", lambda: drawn.append(True))
    monkeypatch.setattr(CompanyForm, "exec", lambda self: 1)
    window.app.db.save_company(name="Prüfdienst GmbH")
    window.company_action.trigger()
    assert drawn == [True] and window.templates.company["name"] == "Prüfdienst GmbH"
