# EasyMeasurement - easymeasurement/l10n/catalog.py
# Language catalogues: one folder per language, its texts spread over several files.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A language lives in data/languages/<code>/.

`language.yaml` holds its own name and its formats. Every other file there adds
texts, keyed by the English source text:

    texts:
      Test instrument: Messgerät
    contexts:
      state:
        Open: offen

`contexts` separates one English word that needs two translations. A file of
another area may repeat a text only with the same translation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import yaml

SOURCE = "en"
SOURCE_NAME = "English"
LANGUAGE_FILE = "language.yaml"
STORED = "stored"  # words of records, plans and templates: needed even where no code names them


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Catalog:
    code: str
    name: str
    formats: dict[str, str] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    contexts: dict[str, dict[str, str]] = field(default_factory=dict)

    def text(self, source: str, context: str = "") -> str | None:
        if context:
            return self.contexts.get(context, {}).get(source)
        return self.texts.get(source)


def folder():
    return resources.files("easymeasurement") / "data" / "languages"


def _read(entry) -> dict:
    return yaml.safe_load(entry.read_text(encoding="utf-8")) or {}


def _merge(target: dict[str, str], found: dict, origin: str) -> None:
    for source, text in (found or {}).items():
        source = str(source)
        text = str(text)
        if target.get(source, text) != text:
            raise CatalogError(f"{origin}: {source!r} translated twice differently")
        target[source] = text


def _reading_order(entry) -> tuple[bool, str]:
    """Stored words come first, so a stored text is traced back to the term records use."""
    return not entry.name.startswith(STORED), entry.name


@cache
def catalog(code: str) -> Catalog:
    """The catalogue of one language; the source language has an empty one."""
    if code == SOURCE:
        return Catalog(SOURCE, SOURCE_NAME)
    root = folder() / code
    head = _read(root / LANGUAGE_FILE)
    texts: dict[str, str] = {}
    contexts: dict[str, dict[str, str]] = {}
    for entry in sorted(root.iterdir(), key=_reading_order):
        if not entry.name.endswith(".yaml") or entry.name == LANGUAGE_FILE:
            continue
        data = _read(entry)
        origin = f"{code}/{entry.name}"
        _merge(texts, data.get("texts"), origin)
        for context, found in (data.get("contexts") or {}).items():
            _merge(contexts.setdefault(str(context), {}), found, origin)
    return Catalog(code, str(head.get("name", code)), dict(head.get("formats") or {}),
                   texts, contexts)


def available(program: bool = False) -> dict[str, str]:
    """Code and own name of every language the program knows, the source first. With
    `program`, only those its user interface is translated into (`program: true`); the others
    serve reports."""
    found = {SOURCE: SOURCE_NAME}
    for entry in sorted(folder().iterdir(), key=lambda e: e.name):
        if not (entry.is_dir() and (entry / LANGUAGE_FILE).is_file()):
            continue
        head = _read(entry / LANGUAGE_FILE)
        if head.get("program") or not program:
            found[entry.name] = str(head.get("name", entry.name))
    return found


@cache
def _sources() -> dict[str, str]:
    """Every translation back to its English text; the first language listed wins a tie."""
    found: dict[str, str] = {}
    for code in available():
        for source, text in catalog(code).texts.items():
            found.setdefault(text, source)
    return found


def source_of(text: str) -> str | None:
    return _sources().get(text)
