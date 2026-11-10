# EasyMeasurement - easymeasurement/reporting/nodes.py
# Document nodes: what a resolved template consists of.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Heading:
    text: str
    level: int = 1


@dataclass
class Paragraph:
    text: str


@dataclass
class Notice:
    text: str


@dataclass
class Fields:
    rows: list[tuple[str, str]]


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    summary: list[list[str]] = field(default_factory=list)


@dataclass
class Photos:
    items: list[tuple]  # file and caption; marks drawn on it and its role, where known


@dataclass
class SignatureLine:
    labels: list[str]
    image: bytes | None = None  # stands over the last label
    result: str = ""  # framed above the lines where given
    tone: str = ""  # "passed" or "failed" colours the result


@dataclass
class Letterhead:
    """The top of the first page: title and code, who ordered the test, who carried it out."""

    title: str
    lines: list[str]
    client: list[str]
    contractor: list[str]
    code: str = ""  # shown as a QR code where given


@dataclass
class Logo:
    """Placed on the page by coordinates, outside the text flow."""

    data: bytes
    x_mm: float
    y_mm: float
    width_mm: float
    every_page: bool = False
    reserve: bool = True


Node = (Heading | Paragraph | Notice | Fields | Table | Photos | SignatureLine | Logo
        | Letterhead)
