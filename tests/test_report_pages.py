# OkeyDocu - tests/test_report_pages.py
# How a report fills its pages: photo rows, signature lines, column widths, the running head.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import shutil
import subprocess
from collections import Counter

import pytest

from okeydocu.reporting.context import ReportStep
from okeydocu.reporting.footnotes import Footnotes
from okeydocu.reporting.measurement_table import group_nodes
from okeydocu.reporting.nodes import Table
from okeydocu.reporting.pdf import render_pdf
from okeydocu.reporting.template import resolve

from .rlo_helpers import photo, rlo


@pytest.mark.skipif(shutil.which("pdfimages") is None, reason="needs pdfimages")
def test_no_page_holds_more_than_two_rows_of_photos(tmp_path):
    group = []
    for n in range(9):
        measurement = rlo(n=n)
        measurement.photos.append(photo(tmp_path / f"{n}.jpg"))
        group.append(measurement)
    lonely = rlo(n=20)
    lonely.photos += [photo(tmp_path / f"x{n}.jpg") for n in range(8)]
    buffer = io.BytesIO()
    render_pdf(group_nodes(group, {}, Footnotes()) + group_nodes([lonely], {}, Footnotes()),
               buffer)
    target = tmp_path / "report.pdf"
    target.write_bytes(buffer.getvalue())
    listing = subprocess.run(["pdfimages", "-list", str(target)], capture_output=True,
                             text=True, timeout=60, check=True).stdout.splitlines()[2:]
    per_page = Counter(line.split()[0] for line in listing)
    assert sum(per_page.values()) == 17
    assert max(per_page.values()) <= 6


def test_a_photo_a_measurement_shows_is_not_shown_again(tmp_path):
    measurement = rlo()
    measurement.photos.append(tmp_path / "a.jpg")
    block = {"type": "steps", "blocks": [{"type": "measurements"}, {"type": "photos"}]}
    step = ReportStep("Schutzleiter", "rlo", "done", "", [measurement])
    (node,) = resolve({"blocks": [block]}, {"campaign": {}, "steps": [step]})
    assert [note.number for note in node.photos] == [1]
    assert ("Bemerkung", "siehe [1]") in node.body.rows


def test_place_date_and_name_are_written_on_the_signature_lines():
    from okeydocu.reporting.template_model import FILLED_PLACE

    block = {"type": "signature", "labels": ["Ort, Datum", "Unterschrift"],
             "fills": [FILLED_PLACE, "{{ campaign.tester }}"]}
    values = {"campaign": {"tester": "Max Prüfer"}, "steps": [], "company": {"city": "Musterstadt"},
              "report": {"date": "01.03.2026"}}
    (node,) = resolve({"blocks": [block]}, values)
    assert node.fills == ["Musterstadt, 01.03.2026", "Max Prüfer"]
    values["company"]["city"] = ""
    assert resolve({"blocks": [block]}, values)[0].fills[0] == "01.03.2026"
    buffer = io.BytesIO()
    render_pdf([node], buffer)
    assert buffer.getvalue().startswith(b"%PDF")


def test_measurement_block_outside_a_repeat_covers_the_campaign():
    template = {"blocks": [{"type": "measurements"}]}
    step = ReportStep("Schutzleiter", "rlo", "done", "", [rlo(n=1), rlo(n=2)])
    values = {"campaign": {}, "steps": [step]}
    head, node = resolve(template, values)
    assert isinstance(node.body, Table) and len(node.body.rows) == 2


def test_the_remarks_take_the_room_the_other_columns_leave():
    from okeydocu.reporting.pdf_tables import column_widths

    headers = ["Nr.", "Zeit", "Bemerkung"]
    rows = [["1", "10:00:00", "kurz"]]
    widths = column_widths(headers, rows, [], 400, ("Helvetica", "Helvetica-Bold"), 8.5, 2)
    assert sum(widths) == pytest.approx(400) and widths[2] > 300
    even = column_widths(headers, rows, [], 400, ("Helvetica", "Helvetica-Bold"), 8.5)
    assert even[2] < 300


def test_the_letterhead_names_the_later_pages():
    from okeydocu.reporting.nodes import Letterhead
    from okeydocu.reporting.pdf_pages import running_head

    head = Letterhead("Prüfprotokoll", ["Prüfung", "Maschine: Presse", "Prüfung vom 01.03.2026"],
                      [], [])
    assert running_head([head]) == (["Prüfprotokoll", "Prüfung", "Maschine: Presse"],
                                    "Prüfung vom 01.03.2026")
    assert running_head([]) == ([], "")


def test_a_long_head_shortens_its_title_and_keeps_what_was_tested():
    from reportlab.pdfbase.pdfmetrics import stringWidth

    from okeydocu.reporting.pdf_pages import ELLIPSIS, fitted_head

    title = "Prüfprotokoll nach einer sehr langen Prüfgrundlage mit vielen Normen " * 3
    parts = [title.strip(), "Wiederholungsprüfung nach Umzug", "Maschine: Presse"]
    right = "Prüfung vom 01.03.2026"
    left = fitted_head(parts, right, "Helvetica")
    assert left.endswith("Wiederholungsprüfung nach Umzug · Maschine: Presse")
    assert ELLIPSIS in left
    room = 595.276 - 2 * (18 * 72 / 25.4 + 6)
    assert stringWidth(left + right, "Helvetica", 7.5) < room
    assert fitted_head(["Kurz", "Presse"], right, "Helvetica") == "Kurz · Presse"


def test_parts_handed_to_the_frame_count_the_room_above_their_heading():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer

    from okeydocu.reporting.pdf_photos import Footnoted, PageBudget

    heading = Paragraph("Schrank", ParagraphStyle("h", spaceBefore=16))
    footnoted = Footnoted(lambda rows, last: Spacer(1, 10 * len(rows)), [1, 2], [0, 0], [],
                          400, PageBudget(), 700, lead=[heading])
    parts = footnoted.parts(2)
    whole, _ = footnoted._measure(parts, 400)
    loose, _ = footnoted._measure(parts, 400, loose=True)
    assert loose == whole + 16


def test_the_name_of_a_standard_is_never_broken():
    from okeydocu.reporting.pdf_tables import kept_standards

    assert kept_standards("nach DIN EN 60204-1 und DIN VDE 0100-600") == (
        "nach DIN\xa0EN\xa060204-1 und DIN\xa0VDE\xa00100-600")
    assert kept_standards("DGUV V3") == "DGUV\xa0V3"
    assert kept_standards("MEN 5 Kabel") == "MEN 5 Kabel"
