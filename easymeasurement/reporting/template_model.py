# EasyMeasurement - easymeasurement/reporting/template_model.py
# What the template editor offers: block types, placeholders, conditions, serialising.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import yaml

from ..l10n import N_, in_language, plural, tr
from .structure import ORDERS

FILLED_PLACE = "{% if company.city %}{{ company.city }}, {% endif %}{{ report.date }}"

BLOCK_LABELS = {
    "heading": N_("Heading"),
    "text": N_("Text"),
    "notice": N_("Notice (red)"),
    "fields": N_("Field list"),
    "steps": N_("Repeat for each step"),
    "measurements": N_("Measurements (0 / 1 / n)"),
    "structure": N_("Measurements by structure"),
    "photos": N_("Photos"),
    "attachments": N_("Notes and attachments on places"),
    "signature": N_("Signature line"),
    "logo": N_("Logo"),
    "letterhead": N_("Letterhead"),
}

# Offered in the editor, so nobody has to know the variable names.
PLACEHOLDERS = [
    (N_("Customer: name"), "{{ customer.name }}"),
    (N_("Customer: street"), "{{ customer.street }}"),
    (N_("Customer: postcode"), "{{ customer.zip }}"),
    (N_("Customer: city"), "{{ customer.city }}"),
    (N_("Order: department"), "{{ campaign.department }}"),
    (N_("Order: cost centre"), "{{ campaign.cost_center }}"),
    (N_("Contact person: name"), "{{ campaign.contact }}"),
    (N_("Contact person: direct line"), "{{ campaign.contact_phone }}"),
    (N_("Contact person: e-mail"), "{{ campaign.contact_email }}"),
    (N_("Own company: name"), "{{ company.name }}"),
    (N_("Own company: street"), "{{ company.street }}"),
    (N_("Own company: postcode"), "{{ company.zip }}"),
    (N_("Own company: city"), "{{ company.city }}"),
    (N_("Own company: phone"), "{{ company.phone }}"),
    (N_("Own company: e-mail"), "{{ company.email }}"),
    (N_("Own company: web"), "{{ company.web }}"),
    (N_("Installation: kind"), "{{ asset.kind_text }}"),
    (N_("Installation: designation"), "{{ asset.name }}"),
    (N_("Installation: identifier"), "{{ asset.identifier }}"),
    (N_("Campaign: title"), "{{ campaign.title }}"),
    (N_("Campaign: test plan"), "{{ campaign.plan }}"),
    (N_("Campaign: inspector"), "{{ campaign.tester }}"),
    (N_("Campaign: start"), "{{ campaign.started }}"),
    (N_("Campaign: day of the test"), "{{ campaign.date }}"),
    (N_("Campaign: completion"), "{{ campaign.closed }}"),
    (N_("Instrument: manufacturer"), "{{ device.manufacturer }}"),
    (N_("Instrument: model"), "{{ device.model }}"),
    (N_("Instrument: serial number"), "{{ device.serial_no }}"),
    (N_("Instrument: firmware"), "{{ device.firmware }}"),
    (N_("Instrument: calibrated on"), "{{ device.calibrated_on }}"),
    (N_("Instrument: recalibration due"), "{{ device.recalibration_due }}"),
    (N_("Instrument: clock"), "{{ campaign.clock_summary }}"),
    (N_("Campaign: record seal"), "{{ campaign.seal }}"),
    (N_("Step: title"), "{{ step.title }}"),
    (N_("Step: reason"), "{{ step.note }}"),
    (N_("Overall result"), "{{ verdict }}"),
    (N_("Report: date"), "{{ report.date }}"),
]

CONDITIONS = [
    (N_("Always show"), None),
    (N_("Only if an instrument is involved"), "device.model"),
    (N_("Only if the calibration is overdue"), "device.overdue"),
    (N_("Only if there are notes or attachments on places"), "places"),
]


def new_block(kind: str) -> dict:
    """A block as it is inserted: its texts in the language of the program."""
    defaults = {
        "heading": {"text": tr("New heading"), "level": 2},
        "text": {"text": tr("New text")},
        "notice": {"text": tr("New notice")},
        "fields": {"rows": [[tr("Designation"), "{{ customer.name }}"]]},
        "steps": {"blocks": []},
        "measurements": {"none": {"text": tr("Not measured.")}, "one": {},
                         "many": {"summary": True}},
        "structure": {"order": "place", "many": {"summary": True}},
        "photos": {},
        "attachments": {},
        "signature": {"result": tr("Test result: {{ verdict }}"),
                      "labels": [tr("Place, date"), tr("Signature of inspector")],
                      "fills": [FILLED_PLACE, "{{ campaign.tester }}"]},
        "letterhead": {
            "title": tr("Test report"),
            "lines": ["{{ campaign.title }}", tr("Tested on {{ campaign.date }}")],
            "client": ["{{ customer.name }}", "{{ customer.street }}",
                       "{{ customer.zip }} {{ customer.city }}",
                       tr("Department: {{ campaign.department }}"),
                       tr("Contact: {{ campaign.contact }}"),
                       tr("Phone: {{ campaign.contact_phone }}"),
                       "{{ campaign.contact_email }}"],
            "contractor": ["{{ company.name }}", "{{ company.street }}",
                           "{{ company.zip }} {{ company.city }}",
                           tr("Cost centre: {{ campaign.cost_center }}"),
                           tr("Inspector: {{ campaign.tester }}")],
            "qr": True,
            "logo": True,
        },
        "logo": {"image": "", "x_mm": 152.0, "y_mm": 8.0, "width_mm": 40.0, "pages": "first",
                 "reserve": True},
    }
    return {"type": kind, **defaults[kind]}


def block_summary(block: dict) -> str:
    label = tr(BLOCK_LABELS[block["type"]]) if block["type"] in BLOCK_LABELS else block["type"]
    text = block.get("text")
    if text:
        short = " ".join(str(text).split())
        for name, code in PLACEHOLDERS:
            short = short.replace(code, f"[{tr(name)}]")
        if len(short) > SUMMARY_LENGTH:
            short = short[:SUMMARY_LENGTH].rstrip() + " …"
        return f"{label}: {short}"
    if block["type"] == "fields":
        return plural(len(block.get("rows", ())), "{label} ({count} line)",
                      "{label} ({count} lines)", label=label)
    if block["type"] == "structure":
        order = tr(ORDERS.get(block.get("order", "place"), block.get("order", "")))
        compact = f", {tr('compact')}" if block.get("layout") == "compact" else ""
        return f"{label}: {order}{compact}"
    if block["type"] == "letterhead":
        title = f"{label}: {block.get('title', '')}"
        return tr("{title} with QR code", title=title) if block.get("qr") else title
    if block["type"] == "logo":
        if not block.get("image"):
            return tr("{label} (no image yet)", label=label)
        pages = tr("every page") if block.get("pages") == "all" else tr("first page")
        width = f"{block.get('width_mm', 0):.0f}"
        return tr("{label} ({width} mm wide, {pages})", label=label, width=width, pages=pages)
    if block.get("when"):
        return tr("{label} (conditional)", label=label)
    return label


SUMMARY_LENGTH = 60  # characters of a block's text shown in the outline
TEXT_KEYS = {"title", "lines", "client", "contractor", "rows", "text", "result", "labels",
             "name"}


def _told(value):
    if isinstance(value, str):
        return in_language(value)
    if isinstance(value, list):
        return [_told(item) for item in value]
    return value


def _localised(node):
    """Texts of the blocks in the current language; keys, conditions and data stay."""
    if isinstance(node, list):
        return [_localised(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {key: _told(value) if key in TEXT_KEYS else _localised(value)
            for key, value in node.items()}


def in_program_language(text: str) -> str:
    """A shipped template as it is stored for its user: worded in the program's language,
    which every report language still recognises."""
    return dump_template(_localised(yaml.safe_load(text)))


def dump_template(template: dict) -> str:
    """Images go last, so the blocks stay readable, and unused ones are dropped."""
    used = {b.get("image") for b in template["blocks"] if b["type"] == "logo"}
    images = {k: v for k, v in (template.get("images") or {}).items() if k in used}
    ordered = {k: v for k, v in template.items() if k != "images"}
    if images:
        ordered["images"] = images
    return yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, width=100)
