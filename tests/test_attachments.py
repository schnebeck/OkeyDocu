# OkeyDocu - tests/test_attachments.py
# Comments, images and PDFs on measurements and places.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PIL import Image

from okeydocu.campaign.attachments import AttachmentError
from okeydocu.store import CampaignClosed


@pytest.fixture
def campaign(service, asset_id):
    return service.create(asset_id, "T", "P")


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "Schaltplan.pdf"
    path.write_bytes(b"%PDF-1.4 test")
    return path


def test_comment_on_a_measurement(service, campaign):
    measurement = service.add_measurement(campaign, "rlo", [])
    service.add_comment(campaign, "Klemme lose", measurement_id=measurement)
    row = service.attachments(campaign, measurement_id=measurement)[0]
    assert (row["kind"], row["text"]) == ("comment", "Klemme lose")


def test_comment_on_a_place(service, campaign, asset_id):
    service.add_comment(campaign, "Schrank verschlossen", asset_id=asset_id)
    assert service.attachments(campaign, asset_id=asset_id)[0]["text"] == "Schrank verschlossen"


def test_pdf_is_copied_into_the_campaign(service, campaign, asset_id, pdf):
    service.add_attachment(campaign, pdf, asset_id=asset_id)
    row = service.attachments(campaign)[0]
    assert (row["kind"], row["original_name"]) == ("pdf", "Schaltplan.pdf")
    assert service.attachment_path(campaign, row["file_name"]).read_bytes() == pdf.read_bytes()


def test_image_is_recognised(service, campaign, tmp_path):
    path = tmp_path / "Typenschild.PNG"
    Image.new("RGB", (4, 4)).save(path, "PNG")
    service.add_attachment(campaign, path)
    assert service.attachments(campaign)[0]["kind"] == "image"


def test_other_files_are_refused(service, campaign, tmp_path):
    path = tmp_path / "liste.xlsx"
    path.write_bytes(b"x")
    with pytest.raises(AttachmentError, match="liste.xlsx"):
        service.add_attachment(campaign, path)
    assert service.attachments(campaign) == []


def test_removing_leaves_the_attachment_loose_in_the_campaign(service, campaign, asset_id, pdf):
    attachment = service.add_attachment(campaign, pdf, asset_id=asset_id)
    service.remove_attachment(attachment)
    assert service.attachments(campaign, asset_id=asset_id) == []
    assert [row["id"] for row in service.loose_attachments(campaign)] == [attachment]


def test_deleting_ends_attachment_and_file(service, campaign, pdf):
    attachment = service.add_attachment(campaign, pdf)
    path = service.attachment_path(campaign, service.attachments(campaign)[0]["file_name"])
    service.delete_attachment(attachment)
    assert service.attachments(campaign) == []
    assert not path.exists()


def test_a_shared_file_stays_until_its_last_attachment_goes(service, campaign, pdf):
    first = service.add_attachment(campaign, pdf)
    second = service.add_attachment(campaign, pdf)
    path = service.attachment_path(campaign, service.attachments(campaign)[0]["file_name"])
    service.delete_attachment(first)
    assert path.exists()
    service.delete_attachment(second)
    assert not path.exists()


def test_a_deleted_measurement_leaves_its_attachment_loose(service, campaign):
    measurement = service.add_measurement(campaign, "rlo", [])
    service.add_comment(campaign, "Text", measurement_id=measurement)
    service.delete_measurement(measurement)
    assert len(service.loose_attachments(campaign)) == 1


def test_closed_campaign_freezes_attachments(service, campaign, pdf):
    attachment = service.add_attachment(campaign, pdf)
    service.close(campaign)
    with pytest.raises(CampaignClosed):
        service.remove_attachment(attachment)
    with pytest.raises(CampaignClosed):
        service.delete_attachment(attachment)
    with pytest.raises(CampaignClosed):
        service.add_comment(campaign, "später")


def sealed(service, campaign, pdf):
    service.add_attachment(campaign, pdf)
    service.close(campaign)


def test_seal_covers_the_attachment_row(service, campaign, pdf):
    sealed(service, campaign, pdf)
    connection = service.db.connection
    connection.execute("DROP TRIGGER attachments_frozen_update")
    connection.execute("UPDATE attachments SET text='gefälscht'")
    connection.commit()
    assert service.check_seal(campaign).rejected


def test_seal_notices_a_changed_file(service, campaign, pdf):
    sealed(service, campaign, pdf)
    row = service.attachments(campaign)[0]
    service.attachment_path(campaign, row["file_name"]).write_bytes(b"anders")
    assert service.check_seal(campaign).rejected


def test_seal_notices_a_missing_file(service, campaign, pdf):
    sealed(service, campaign, pdf)
    row = service.attachments(campaign)[0]
    service.attachment_path(campaign, row["file_name"]).unlink()
    assert service.check_seal(campaign).rejected
