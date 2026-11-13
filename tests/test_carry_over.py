# OkeyDocu - tests/test_carry_over.py
# Notes and files of the last confirmed inspection, offered again and copied on request.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.ui.place_files import EARLIER, PlaceFiles


@pytest.fixture
def earlier(app, tmp_path):
    """A confirmed inspection of a press with a note and a plan at its cabinet."""
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    first = app.service.create(press, "2026", "Anna Prüfer")
    plan = tmp_path / "Schaltplan.pdf"
    plan.write_bytes(b"%PDF-1.4\n%%EOF\n")
    app.service.add_attachment(first, plan, asset_id=cabinet)
    app.service.add_comment(first, "Schlüssel beim Hausmeister", asset_id=cabinet)
    measured = app.service.add_measurement(first, "rlo", [], datetime(2026, 5, 4, 9, 0),
                                           asset_id=cabinet)
    sheet = tmp_path / "Datenblatt.pdf"
    sheet.write_bytes(b"%PDF-1.4\n% sheet\n%%EOF\n")
    app.service.add_attachment(first, sheet, measurement_id=measured)
    app.service.close(first)
    second = app.service.create(press, "2027", "Anna Prüfer")
    return {"press": press, "cabinet": cabinet, "first": first, "second": second}


def _names(rows):
    return sorted(row["text"] or row["original_name"] for row in rows)


def test_the_last_inspection_offers_what_lay_at_the_element(app, earlier):
    rows = app.service.earlier_attachments(earlier["second"], earlier["cabinet"])
    assert _names(rows) == ["Datenblatt.pdf", "Schaltplan.pdf", "Schlüssel beim Hausmeister"]
    assert app.service.earlier_attachments(earlier["second"], earlier["press"]) == []


def test_taking_over_copies_it_and_leaves_the_sealed_one_alone(app, earlier):
    plan = next(r for r in app.service.earlier_attachments(earlier["second"], earlier["cabinet"])
                if r["original_name"] == "Schaltplan.pdf")
    app.service.take_over_attachment(earlier["second"], plan["id"], earlier["cabinet"])
    copy = app.service.attachments(earlier["second"], asset_id=earlier["cabinet"])[0]
    assert copy["original_name"] == "Schaltplan.pdf" and copy["sha256"] == plan["sha256"]
    assert app.service.attachment_path(earlier["second"], copy["file_name"]).exists()
    left = app.service.earlier_attachments(earlier["second"], earlier["cabinet"])
    assert _names(left) == ["Datenblatt.pdf", "Schlüssel beim Hausmeister"]
    assert len(app.service.attachments(earlier["first"])) == 3
    assert app.service.check_seal(earlier["first"]).rejected is False


def test_a_first_inspection_has_nothing_to_offer(app, earlier):
    assert app.service.earlier_attachments(earlier["first"], earlier["cabinet"]) == []


def test_the_place_list_shows_them_greyed_and_takes_one_over(app, earlier, qtbot):
    files = PlaceFiles(app, "Schrank")
    qtbot.addWidget(files)
    files.show_target(earlier["second"], True, asset_id=earlier["cabinet"])
    items = [files.list.item(i) for i in range(files.list.count())]
    assert len(items) == 3 and all(item.data(EARLIER) for item in items)
    assert not files.take_button.isHidden() and not files.take_button.isEnabled()
    assert files.remove_button.isHidden()
    files.list.setCurrentRow(0)
    assert files.take_button.isEnabled()
    files._remove()  # never touches the sealed inspection
    assert len(app.service.attachments(earlier["first"])) == 3
    files._take_over()
    own = [files.list.item(i) for i in range(files.list.count())
           if not files.list.item(i).data(EARLIER)]
    assert len(own) == 1 and files.list.count() == 3


def test_a_closed_campaign_shows_no_earlier_entries(app, earlier, qtbot):
    files = PlaceFiles(app, "Schrank")
    qtbot.addWidget(files)
    files.show_target(earlier["second"], False, asset_id=earlier["cabinet"])
    assert files.list.count() == 0 and files.take_button.isHidden()
