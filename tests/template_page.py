# EasyMeasurement - tests/template_page.py
# The template editor in the real window, with a template that repeats per step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from easymeasurement.__main__ import build_context
from easymeasurement.reporting.template import default_template_text
from easymeasurement.reporting.template_model import in_program_language
from easymeasurement.ui.main_window import MainWindow

# The repeat these tests work in, in place of the standard template's structure block.
STEPS = """  - type: steps
    blocks:
      - type: heading
        level: 2
        text: "{{ step.title }}"
      - type: measurements
        none:
          text: "Not measured.{% if step.note %} Reason: {{ step.note }}{% endif %}"
        one: {}
        many:
          summary: true
      - type: photos
"""


def with_repeat() -> str:
    text = default_template_text()
    start = text.index("  - type: structure")
    end = text.index("  - type: heading", start)
    return text[:start] + STEPS + text[end:]


def open_template_page(qtbot):
    """The templates page of a window whose standard template repeats per step."""
    app = build_context()
    app.db.save_template(app.db.templates()[0]["name"], in_program_language(with_repeat()))
    main = MainWindow(app)
    qtbot.addWidget(main)
    main.open_page(main.templates)
    yield main.templates
    app.db.close()
