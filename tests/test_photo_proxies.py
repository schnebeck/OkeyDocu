# EasyMeasurement - tests/test_photo_proxies.py
# Reduced copies of photos: made once, made again when the original changes, tidied away.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from datetime import datetime

from PIL import Image

from easymeasurement.campaign import photo_proxies
from easymeasurement.campaign.photo_proxies import (
    EDGE_PX,
    fresh_proxy,
    make_proxy,
    prune_proxies,
    proxy_path,
)
from easymeasurement.reporting.template import default_template_text


def _original(folder, name="a1b2c3.jpg", size=(3000, 2000), orientation=1):
    (folder / "photos").mkdir(parents=True, exist_ok=True)
    path = folder / "photos" / name
    exif = Image.Exif()
    exif[0x0112] = orientation
    Image.new("RGB", size, "red").save(path, exif=exif.tobytes())
    return path


def test_a_proxy_is_upright_small_and_made_only_once(tmp_path, monkeypatch):
    original = _original(tmp_path, orientation=6)
    proxy = make_proxy(original)
    assert proxy == proxy_path(original) and proxy.parent.name == "proxies"
    with Image.open(proxy) as image:
        assert max(image.size) == EDGE_PX and image.height > image.width  # turned upright
    assert proxy.stat().st_mtime_ns == original.stat().st_mtime_ns
    monkeypatch.setattr(photo_proxies, "reduced", lambda path: 1 / 0)  # must not be needed
    assert make_proxy(original) == proxy


def test_a_changed_original_gets_a_new_proxy(tmp_path):
    original = _original(tmp_path)
    make_proxy(original)
    Image.new("RGB", (800, 600), "blue").save(original)
    stamp = original.stat().st_mtime_ns + 1_000_000_000
    os.utime(original, ns=(stamp, stamp))
    assert fresh_proxy(original) is None
    with Image.open(make_proxy(original)) as image:
        assert image.size == (800, 600) and image.getpixel((5, 5))[2] > 200


def test_a_file_outside_a_campaign_gets_no_proxy(tmp_path):
    loose = tmp_path / "loose.jpg"
    Image.new("RGB", (100, 100)).save(loose)
    assert make_proxy(loose) is None and proxy_path(loose) is None
    assert sorted(p.name for p in tmp_path.iterdir()) == ["loose.jpg"]


def test_pruning_keeps_only_proxies_of_present_originals(tmp_path):
    kept = _original(tmp_path, "keep.jpg")
    gone = _original(tmp_path, "gone.jpg")
    make_proxy(kept)
    make_proxy(gone)
    proxies = tmp_path / "proxies"
    (proxies / "keep-800.jpg").write_bytes(b"other size")
    (proxies / "keep-1400.jpg.1-2.part").write_bytes(b"left by a process long gone")
    working = proxies / f"keep-1400.jpg.{os.getpid()}-7.part"
    working.write_bytes(b"still being written")
    assert prune_proxies(tmp_path, [kept]) == 3
    assert sorted(p.name for p in proxies.iterdir()) == sorted(
        [proxy_path(kept).name, working.name])


def test_deleting_a_photo_takes_its_proxy_along(service, tmp_path):
    asset = service.db.add_asset(service.db.add_customer("K"), "machine", "M")
    campaign = service.create(asset, "P", "T")
    measurement = service.add_measurement(campaign, "rlo", [], datetime(2026, 5, 4, 9, 0))
    source = tmp_path / "foto.jpg"
    Image.new("RGB", (2000, 1500), "green").save(source)
    service.add_photo(measurement, source)
    row = service.photos(campaign)[0]
    original = service.photo_path(campaign, row["file_name"])
    proxy = make_proxy(original)
    assert proxy.exists()
    service.delete_photo(row["id"])
    assert not proxy.exists()


def test_a_report_makes_the_proxies_and_tidies_strays(service, tmp_path):
    from easymeasurement.reporting.archive import ReportArchive
    asset = service.db.add_asset(service.db.add_customer("K"), "machine", "M")
    campaign = service.create(asset, "P", "T")
    measurement = service.add_measurement(campaign, "rlo", [], datetime(2026, 5, 4, 9, 0))
    source = tmp_path / "foto.jpg"
    Image.new("RGB", (2400, 1800), "green").save(source)
    service.add_photo(measurement, source)
    stray = service.folder(campaign) / "proxies" / "deadbeef-1400.jpg"
    stray.parent.mkdir()
    stray.write_bytes(b"x")
    ReportArchive(service).draft(campaign, default_template_text())
    original = service.picture_files(campaign)[0]
    assert fresh_proxy(original) is not None and not stray.exists()


def test_the_draft_waits_for_the_proxies_and_the_status_line_counts_them(window, app):
    from concurrent.futures import Future
    asset = app.db.add_asset(app.db.add_customer("K"), "machine", "M")
    campaign = app.service.create(asset, "P", "T")
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert page.draft_action.isEnabled() and page.header.draft_button.isEnabled()
    first, second = Future(), Future()
    first.set_result(None)
    page.proxies.follow(campaign, [first, second])
    assert not page.draft_action.isEnabled() and not page.header.draft_button.isEnabled()
    assert page.proxy_note.text() == "Bereite Fotos für das Protokoll vor: 1 von 2"
    second.set_result(None)
    page.proxies._poll()
    assert page.draft_action.isEnabled() and page.proxy_note.isHidden()
