# OkeyDocu - tests/test_report_legend.py
# l10n: de
# The legend below the summary of a report explains only what the report shows.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from okeydocu.reporting.context import build_context
from okeydocu.reporting.language import speaking
from okeydocu.reporting.nodes import Paragraph, plain
from okeydocu.reporting.template import default_template_text, parse_template, resolve

from .photo_ui_helpers import make_campaign, photo_ids


def legend(app, campaign) -> str:
    with speaking("de"):
        nodes = resolve(parse_template(default_template_text()),
                        build_context(app.service, campaign))
    texts = [plain(node.text) for node in nodes if isinstance(node, Paragraph)]
    return next(text for text in texts if "bestanden" in text and "ISO 80000" in text)


def test_photos_are_explained_where_the_report_has_some(app, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    app.service.pin_photo(photo_ids(app, campaign)[0], measured[0])
    assert "etwa [1], verweist auf das Foto mit dieser Nummer" in legend(app, campaign)


def test_a_report_without_photos_says_nothing_about_them(app, asset, tmp_path):
    campaign, _ = make_campaign(app, asset, tmp_path, photos=())
    told = legend(app, campaign)
    assert "Foto" not in told
    assert told.startswith("✓ bestanden") and told.endswith("nennt die Messgröße")
