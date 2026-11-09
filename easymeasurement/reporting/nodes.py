# EasyMeasurement - easymeasurement/reporting/nodes.py
# Document nodes: what a resolved template consists of.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    items: list[tuple[Path, str]]  # file and caption


@dataclass
class SignatureLine:
    labels: list[str]
    image: bytes | None = None  # stands over the last label


@dataclass
class Logo:
    """Placed on the page by coordinates, outside the text flow."""

    data: bytes
    x_mm: float
    y_mm: float
    width_mm: float
    every_page: bool = False
    reserve: bool = True


Node = Heading | Paragraph | Notice | Fields | Table | Photos | SignatureLine | Logo
