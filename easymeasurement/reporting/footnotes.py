# EasyMeasurement - easymeasurement/reporting/footnotes.py
# Photos numbered through a report, referred to by the measurements they belong to.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A photo gets its number where a measurement first refers to it, as `[3]`. Its marks keep
their own numbers, so a remark can say `see note 1 in [3]`, and the list of their texts
stands under the photo."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..campaign.photo_marks import ROLES
from ..l10n import plural, tr
from ..vocabulary import function_markup
from .measurement_words import when
from .nodes import Markup, PhotoNote


def references(photos: list[tuple[int, list[int]]]) -> list[str]:
    """`see [3], [4]` for photos as they are, `see note 1 in [5]` for marks in one."""
    plain = ", ".join(f"[{number}]" for number, notes in photos if not notes)
    found = [tr("see {photos}", photos=plain)] if plain else []
    for number, notes in photos:
        if notes:
            listed = ", ".join(str(note) for note in notes)
            found.append(plural(len(notes), "see note {notes} in [{number}]",
                                "see notes {notes} in [{number}]", notes=listed, number=number))
    return found


class Footnotes:
    def __init__(self):
        self.count = 0
        self.shown: set[str] = set()

    def take(self, measurement) -> tuple[list[PhotoNote], list[str]]:
        """The measurement's photos not shown yet, and how its remark refers to them."""
        taken, numbers = [], []
        for path in measurement.photos:
            if str(path) in self.shown:
                continue
            self.shown.add(str(path))
            self.count += 1
            role, marks, *view = measurement.photo_notes.get(str(path), ("", []))
            caption = f"[{self.count}] {function_markup(measurement.data.function, short=True)}"
            caption += f" · {escape(when(measurement))}"
            if role:
                caption = f"<b>{escape(tr(ROLES[role]))}:</b> {caption}"
            noted = [mark for mark in marks if mark.text]
            taken.append(PhotoNote(path, self.count, Markup(caption),
                                   [f"{mark.number}  {mark.text}" for mark in noted], marks, role,
                                   view[0] if view else None))
            numbers.append((self.count, [mark.number for mark in noted]))
        return taken, references(numbers)
