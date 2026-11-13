# OkeyDocu - tests/test_l10n.py
# Every text the program translates has a German entry with the same placeholders.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import re
import string
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from okeydocu import l10n
from okeydocu.l10n.catalog import STORED, catalog, folder
from okeydocu.store.choice_lists import shipped_choice_texts
from okeydocu.vocabulary.terms import GROUPS, vocabulary

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


def vocabulary_texts() -> tuple[set[str], set[str]]:
    """Names of the vocabulary, which every language has to know, and its symbols, which
    a language may write its own way."""
    words = vocabulary()
    terms = [term for group in GROUPS for term in getattr(words, group).values()]
    return {term.name for term in terms}, {term.symbol for term in terms if term.symbol}


def test_every_name_of_the_vocabulary_has_a_german_entry():
    names, _ = vocabulary_texts()
    missing = sorted(name for name in names if catalog("de").text(name) is None)
    assert not missing, "\n".join(missing)


def shipped_plan_words() -> set[str]:
    """The words of the shipped plans and of the drivers' instructions."""
    from okeydocu.campaign.plan import builtin_plan_texts
    from okeydocu.campaign.plan_language import words
    from okeydocu.devices.registry import instruction_folders
    raws = [yaml.safe_load(text) for text in builtin_plan_texts()]
    raws += [yaml.safe_load(entry.read_text(encoding="utf-8")) for folder in instruction_folders()
             for entry in folder.iterdir() if entry.name.endswith(".yaml")]
    found = set()
    for raw in raws:
        found |= set(words(raw))
        for step in raw.get("steps") or ():
            found |= set(words(step))
    return found


NEEDS_WORDS = re.compile(r"[a-zäöüß]{2}|\d[.,]\d")  # a sign, a socket or a voltage reads the same


def test_every_word_of_the_shipped_plans_has_a_german_entry():
    missing = sorted(text for text in shipped_plan_words()
                     if NEEDS_WORDS.search(text) and catalog("de").text(text) is None)
    assert not missing, "\n".join(missing)


def test_every_text_of_the_shipped_choice_lists_has_a_german_entry():
    missing = sorted(text for text in shipped_choice_texts()
                     if NEEDS_WORDS.search(text) and catalog("de").text(text) is None)
    assert not missing, "\n".join(missing)


def test_every_german_entry_is_used():
    names, symbols = vocabulary_texts()
    used = {(text, context) for _, text, context in marked_texts()}
    used |= {(text, "") for text in names | symbols | shipped_plan_words() | shipped_choice_texts()}
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


def test_telling_a_translation_reads_no_file(monkeypatch):
    """Kinds and features ask this for every label, so it answers from what was read once."""
    import importlib
    catalogs = importlib.import_module("okeydocu.l10n.catalog")
    l10n.available()

    def no_file(entry):
        raise AssertionError(f"read {entry}")

    monkeypatch.setattr(catalogs, "_read", no_file)
    assert l10n.is_translation("Verteiler", "Distribution board")
    assert "de" in l10n.available(program=True)


def test_the_program_offers_only_languages_its_interface_speaks(qtbot, tmp_path, monkeypatch):
    from okeydocu.ui import language_choice
    from PySide6.QtCore import QSettings
    stored = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(language_choice, "settings", lambda: stored)
    overlay = language_choice.LanguageOverlay()
    qtbot.addWidget(overlay)
    choice = overlay.choice
    assert [choice.itemData(i) for i in range(choice.count())] == ["", "en", "de"]
    assert choice.currentIndex() == 0  # nothing chosen yet: as the system
    choice.setCurrentIndex(1)
    assert overlay.hint.text() == "Applies from the next start."  # in the language chosen
    choice.setCurrentIndex(2)
    assert overlay.hint.text() == "Gilt ab dem nächsten Start."
    choice.setCurrentIndex(1)
    overlay.accept()
    assert stored.value(language_choice.KEY) == "en"
    assert language_choice.chosen_language() == "en"
    stored.setValue(language_choice.KEY, language_choice.SYSTEM)
    assert language_choice.chosen_language() == language_choice.system_language()
