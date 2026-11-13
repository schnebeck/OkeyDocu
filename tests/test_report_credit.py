# OkeyDocu - tests/test_report_credit.py
# The upright line naming the program and its tagline at the edge of a report's first page.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import shutil
import subprocess

import pytest
from reportlab.lib.pagesizes import A4

from okeydocu import APP_NAME, TAGLINE
from okeydocu.l10n import speaking
from okeydocu.reporting.pdf import render_pdf
from okeydocu.reporting.template import Heading

pytestmark = pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs pdftotext")


def first_page(path, *options):
    return subprocess.run(["pdftotext", *options, "-f", "1", "-l", "1", str(path), "-"],
                          capture_output=True, text=True, check=True, timeout=30).stdout


def test_the_first_page_names_the_program_with_its_tagline(tmp_path):
    path = tmp_path / "report.pdf"
    with speaking("de"):
        render_pdf([Heading("Prüfprotokoll")], path)
    text = " ".join(first_page(path, "-raw").split())
    assert f"Protokoll erstellt mit {APP_NAME} · {TAGLINE}" in text


def test_the_upright_line_stays_on_the_sheet(tmp_path):
    path = tmp_path / "report.pdf"
    with speaking("en"):
        render_pdf([Heading("Test report")], path)
    words = re.findall(r'yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">([^<]*)<',
                       first_page(path, "-bbox"))
    credit = [(float(low), float(high)) for low, high, word in words
              if word in ("Report", "go")]
    assert len(credit) == 2
    assert all(0 < low and high < A4[1] for low, high in credit)
