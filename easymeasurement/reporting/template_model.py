# EasyMeasurement - easymeasurement/reporting/template_model.py
# What the template editor offers: block types, placeholders, conditions, serialising.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import yaml

BLOCK_LABELS = {
    "heading": "Überschrift",
    "text": "Text",
    "notice": "Hinweis (rot)",
    "fields": "Feldliste",
    "steps": "Je Messschritt wiederholen",
    "measurements": "Messungen (0 / 1 / n)",
    "photos": "Fotos",
    "attachments": "Notizen und Anhänge zu Orten",
    "signature": "Unterschriftszeile",
    "logo": "Logo",
    "letterhead": "Briefkopf",
}

# Offered in the editor, so nobody has to know the variable names.
PLACEHOLDERS = [
    ("Kunde: Name", "{{ customer.name }}"),
    ("Kunde: Straße", "{{ customer.street }}"),
    ("Kunde: PLZ", "{{ customer.zip }}"),
    ("Kunde: Ort", "{{ customer.city }}"),
    ("Auftrag: Abteilung", "{{ campaign.department }}"),
    ("Auftrag: Kostenstelle", "{{ campaign.cost_center }}"),
    ("Ansprechpartner: Name", "{{ campaign.contact }}"),
    ("Ansprechpartner: Durchwahl", "{{ campaign.contact_phone }}"),
    ("Ansprechpartner: E-Mail", "{{ campaign.contact_email }}"),
    ("Eigene Firma: Name", "{{ company.name }}"),
    ("Eigene Firma: Straße", "{{ company.street }}"),
    ("Eigene Firma: PLZ", "{{ company.zip }}"),
    ("Eigene Firma: Ort", "{{ company.city }}"),
    ("Eigene Firma: Telefon", "{{ company.phone }}"),
    ("Eigene Firma: E-Mail", "{{ company.email }}"),
    ("Eigene Firma: Internet", "{{ company.web }}"),
    ("Anlage: Art", "{{ asset.kind_text }}"),
    ("Anlage: Bezeichnung", "{{ asset.name }}"),
    ("Anlage: Kennung", "{{ asset.identifier }}"),
    ("Kampagne: Titel", "{{ campaign.title }}"),
    ("Kampagne: Messplan", "{{ campaign.plan }}"),
    ("Kampagne: Prüfer", "{{ campaign.tester }}"),
    ("Kampagne: Beginn", "{{ campaign.started }}"),
    ("Kampagne: Abschluss", "{{ campaign.closed }}"),
    ("Messgerät: Hersteller", "{{ device.manufacturer }}"),
    ("Messgerät: Modell", "{{ device.model }}"),
    ("Messgerät: Seriennummer", "{{ device.serial_no }}"),
    ("Messgerät: Firmware", "{{ device.firmware }}"),
    ("Messgerät: Kalibriert am", "{{ device.calibrated_on }}"),
    ("Messgerät: Rekalibrierung fällig", "{{ device.recalibration_due }}"),
    ("Messgerät: Uhr", "{{ campaign.clock_summary }}"),
    ("Kampagne: Datensatz-Siegel", "{{ campaign.seal }}"),
    ("Messschritt: Titel", "{{ step.title }}"),
    ("Messschritt: Begründung", "{{ step.note }}"),
    ("Gesamtergebnis", "{{ verdict }}"),
]

CONDITIONS = [
    ("Immer anzeigen", None),
    ("Nur wenn ein Messgerät beteiligt ist", "device.model"),
    ("Nur wenn die Kalibrierung überfällig ist", "device.overdue"),
    ("Nur wenn es Notizen oder Anhänge zu Orten gibt", "places"),
]


def new_block(kind: str) -> dict:
    defaults = {
        "heading": {"text": "Neue Überschrift", "level": 2},
        "text": {"text": "Neuer Text"},
        "notice": {"text": "Neuer Hinweis"},
        "fields": {"rows": [["Bezeichnung", "{{ customer.name }}"]]},
        "steps": {"blocks": []},
        "measurements": {"none": {"text": "Nicht gemessen."}, "one": {}, "many": {"summary": True}},
        "photos": {},
        "attachments": {},
        "signature": {"result": "Ergebnis der Prüfung: {{ verdict }}",
                      "labels": ["Ort, Datum", "Unterschrift {{ campaign.tester }}"]},
        "letterhead": {
            "title": "Prüfprotokoll",
            "lines": ["{{ campaign.title }}", "Prüfung vom {{ campaign.started }}"],
            "client": ["{{ customer.name }}", "{{ customer.street }}",
                       "{{ customer.zip }} {{ customer.city }}",
                       "Abteilung: {{ campaign.department }}",
                       "Ansprechpartner: {{ campaign.contact }}",
                       "Telefon: {{ campaign.contact_phone }}",
                       "{{ campaign.contact_email }}"],
            "contractor": ["{{ company.name }}", "{{ company.street }}",
                           "{{ company.zip }} {{ company.city }}",
                           "Kostenstelle: {{ campaign.cost_center }}",
                           "Prüfer: {{ campaign.tester }}"],
            "qr": True,
            "logo": True,
        },
        "logo": {"image": "", "x_mm": 152.0, "y_mm": 8.0, "width_mm": 40.0, "pages": "first",
                 "reserve": True},
    }
    return {"type": kind, **defaults[kind]}


def block_summary(block: dict) -> str:
    label = BLOCK_LABELS.get(block["type"], block["type"])
    text = block.get("text")
    if text:
        short = " ".join(str(text).split())
        for name, code in PLACEHOLDERS:
            short = short.replace(code, f"[{name}]")
        return f"{label}: {short[:60]}"
    if block["type"] == "fields":
        return f"{label} ({len(block.get('rows', ()))} Zeilen)"
    if block["type"] == "letterhead":
        return f"{label}: {block.get('title', '')}" + (" mit QR-Code" if block.get("qr") else "")
    if block["type"] == "logo":
        if not block.get("image"):
            return f"{label} (noch kein Bild)"
        pages = "jede Seite" if block.get("pages") == "all" else "erste Seite"
        return f"{label} ({block.get('width_mm', 0):.0f} mm breit, {pages})"
    if block.get("when"):
        return f"{label} (bedingt)"
    return label


def dump_template(template: dict) -> str:
    """Images go last, so the blocks stay readable, and unused ones are dropped."""
    used = {b.get("image") for b in template["blocks"] if b["type"] == "logo"}
    images = {k: v for k, v in (template.get("images") or {}).items() if k in used}
    ordered = {k: v for k, v in template.items() if k != "images"}
    if images:
        ordered["images"] = images
    return yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, width=100)
