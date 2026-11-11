# EasyMeasurement - easymeasurement/reporting/nodes.py
# Document nodes: what a resolved template consists of.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

_TAG = re.compile(r"<[^>]+>")


class Markup(str):
    """Text with the inline tags <i>, <b>, <sub> and <sup>, its other characters escaped.
    Every other text of a node is plain and escaped where it is drawn."""

    def plain(self) -> str:
        """The text without its tags, a line break kept as one."""
        return unescape(_TAG.sub("", self.replace("<br/>", "\n")))

    def __html__(self) -> str:
        """Lets a template take it as it is, where everything else is escaped."""
        return str(self)


def plain(text: str) -> str:
    return text.plain() if isinstance(text, Markup) else text


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
    stretch: int | None = None  # the column that takes the room the others leave


@dataclass
class Photos:
    items: list[tuple]  # file and caption; marks drawn on it and its role, where known


@dataclass
class PhotoNote:
    """A photo a measurement refers to by its number, with the texts of its marks."""

    path: Path
    number: int
    caption: str
    notes: list[str] = field(default_factory=list)
    marks: list = field(default_factory=list)
    role: str = ""
    view: object = None  # how the photo is turned and cut; None shows it as it is


@dataclass
class Footnoted:
    """A table or field list and the photos its rows refer to: the PDF sets each photo on the
    page of the first row that names it. `refs` holds, row by row, indices into `photos`."""

    body: "Table | Fields"
    photos: list[PhotoNote]
    refs: list[list[int]]


@dataclass
class SignatureLine:
    labels: list[str]
    image: bytes | None = None  # stands over the last label
    result: str = ""  # framed above the lines where given
    tone: str = ""  # "passed" or "failed" colours the result
    fills: list[str] = field(default_factory=list)  # written on the lines, such as place and date


@dataclass
class Letterhead:
    """The top of the first page: title and code, who ordered the test, who carried it out."""

    title: str
    lines: list[str]
    client: list[str]
    contractor: list[str]
    code: str = ""  # shown as a QR code where given
    logo: bytes | None = None  # the firm's logo, at the right of the title


@dataclass
class Logo:
    """Placed on the page by coordinates, outside the text flow."""

    data: bytes
    x_mm: float
    y_mm: float
    width_mm: float
    every_page: bool = False
    reserve: bool = True


Node = (Heading | Paragraph | Notice | Fields | Table | Photos | Footnoted | SignatureLine
        | Logo | Letterhead)
