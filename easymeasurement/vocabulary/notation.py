# EasyMeasurement - easymeasurement/vocabulary/notation.py
# Symbols of quantities written as in mathematics: italic letter, upright index.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The vocabulary writes a symbol as `R_LO`, `ΔR_LO`, `U_L1-L2` or `R_LO^+`: one letter for
the quantity, `_` before its subscript and `^` before its superscript. Following ISO 80000
the letter is italic; Δ, the indices, numbers and words stay upright, as they name and do
not stand for a quantity. A symbol of several words is read word by word, so `RCD U_IΔN`
is the word RCD followed by a symbol; after a number come units, as in `R_LO 25 A`, which
stay upright like anything else that is no symbol.

`plain` gives the symbol for places without type styles, such as a table on screen;
`markup` gives it with the tags `<i>`, `<sub>` and `<sup>` that both the report and Qt read.
The number of an outer conductor is set low as well, also inside an index: U_L1-L2 has
L₁ and L₂ in its subscript.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from xml.sax.saxutils import escape

_SYMBOL = re.compile(r"^(Δ?)([A-Za-zΑ-Ωα-ω])(?:_([^\s^_]+))?(?:\^(\S+))?$")
_LINE = re.compile(r"(?<![A-Za-z])L([1-3])")  # the number of an outer conductor


@dataclass(frozen=True)
class Part:
    text: str
    italic: bool = False
    position: str = ""  # "sub", "sup" or "" on the line


def parts(symbol: str) -> list[Part]:
    found: list[Part] = []
    units = False
    for index, word in enumerate(symbol.split(" ")):
        if index:
            found.append(Part(" "))
        units = units or word[:1].isdigit()
        match = None if units else _SYMBOL.match(word)
        if not match:
            found.append(Part(word))
            continue
        delta, letter, low, high = match.groups()
        if delta:
            found.append(Part(delta))
        found.append(Part(letter, italic=True))
        if low:
            found.append(Part(low, position="sub"))
        if high:
            found.append(Part(high, position="sup"))
    return found


def _plain_index(text: str) -> str:
    """An index that is a word keeps its mark, as `I_clamp`; one of several parts gets a
    hyphen between them, as `RLO-offset`."""
    if text.isalpha() and sum(letter.islower() for letter in text) > 1:
        return f"_{text}"
    return text.replace(",", "-")


def plain(symbol: str) -> str:
    """`R_LO` as RLO, where nothing can be set low."""
    return "".join(_plain_index(part.text) if part.position else part.text
                   for part in parts(symbol))


# Lowered by a share of the font size: less than the usual half, so an index, and the number
# of a conductor inside it, stays within the line of a table.
LOW = "<sub rise='30%'>"
LOWER = "<sub rise='20%'>"


def conductors(text: str, low: str = LOW) -> str:
    """Text with the numbers of the outer conductors set low, as L₁-PE."""
    return _LINE.sub(lambda match: f"L{low}{match.group(1)}</sub>", escape(text))


def markup(symbol: str) -> str:
    pieces = []
    for part in parts(symbol):
        text = conductors(part.text, LOWER) if part.position == "sub" else escape(part.text)
        if part.italic:
            text = f"<i>{text}</i>"
        if part.position == "sub":
            text = f"{LOW}{text}</sub>"
        elif part.position:
            text = f"<sup>{text}</sup>"
        pieces.append(text)
    return "".join(pieces)


def is_marked(symbol: str) -> bool:
    """Whether the symbol needs type styles to be written correctly."""
    return any(part.italic or part.position for part in parts(symbol))
