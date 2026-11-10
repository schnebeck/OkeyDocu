# EasyMeasurement - tests/test_l10n.py
# Every text the program translates has a German entry with the same placeholders.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import string
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from easymeasurement import l10n
from easymeasurement.l10n.catalog import STORED, catalog, folder

PACKAGE = Path(l10n.__file__).parents[1]
MARKERS = {"tr": (0,), "plural": (1, 2), "N_": (0,)}


def _uses_l10n(tree: ast.Module) -> bool:
    return any(isinstance(node, ast.ImportFrom) and (node.module or "").endswith("l10n")
               for node in ast.walk(tree))


def _context(call: ast.Call) -> str:
    for keyword in call.keywords:
        if keyword.arg == "context" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return ""


def marked_texts():
    """(file, line, text, context) of every literal text handed to tr, plural or N_."""
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _uses_l10n(tree):
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            for index in MARKERS.get(node.func.id, ()):
                if index < len(node.args) and isinstance(node.args[index], ast.Constant):
                    where = f"{path.relative_to(PACKAGE)}:{node.lineno}"
                    yield where, node.args[index].value, _context(node)


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def test_every_marked_text_has_a_german_entry_with_the_same_placeholders():
    german = catalog("de")
    missing, broken = [], []
    for where, text, context in marked_texts():
        translated = german.text(text, context)
        if translated is None:
            missing.append(f"{where} {text!r}")
        elif _fields(translated) != _fields(text):
            broken.append(f"{where} {text!r} -> {translated!r}")
    assert not missing, "\n".join(missing)
    assert not broken, "\n".join(broken)


def _stored_words(code: str) -> set[str]:
    """Words of records, plans and templates: looked up in both directions, used by data."""
    found = set()
    for path in (folder() / code).iterdir():
        if path.name.startswith(STORED):
            found |= set((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("texts", {}))
    return found


def test_every_german_entry_is_used():
    used = {(text, context) for _, text, context in marked_texts()}
    german = catalog("de")
    stored = _stored_words("de")
    unused = [text for text in german.texts if (text, "") not in used and text not in stored]
    unused += [f"{context}: {text}" for context, texts in german.contexts.items()
               for text in texts if (text, context) not in used]
    assert not unused, "\n".join(unused)


def test_texts_follow_the_language_and_fall_back_to_english():
    with l10n.speaking("de"):
        assert l10n.day(date(2026, 3, 4)) == "04.03.2026"
        assert l10n.moment(datetime(2026, 3, 4, 5, 6)) == "04.03.2026 05:06"
        assert l10n.decimal(2.5) == "2,5"
        assert l10n.tr("A text nobody translated") == "A text nobody translated"
    with l10n.speaking("en"):
        assert l10n.day(date(2026, 3, 4)) == "2026-03-04"
        assert l10n.plural(2, "{count} photo", "{count} photos") == "2 photos"


@pytest.mark.parametrize("code", ["de"])
def test_a_language_names_itself(code):
    assert l10n.available()[code] == catalog(code).name


def test_the_program_offers_only_languages_its_interface_speaks(qtbot, tmp_path, monkeypatch):
    from easymeasurement.ui import language_choice
    from PySide6.QtCore import QSettings
    stored = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(language_choice, "settings", lambda: stored)
    overlay = language_choice.LanguageOverlay()
    qtbot.addWidget(overlay)
    choice = overlay.choice
    assert [choice.itemData(i) for i in range(choice.count())] == ["en", "de"]
    choice.setCurrentIndex(0)
    overlay.accept()
    assert stored.value(language_choice.KEY) == "en"
