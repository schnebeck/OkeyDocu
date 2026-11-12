# EasyMeasurement - easymeasurement/store/database.py
# SQLite store: master data, campaigns, measurements, photos, reports.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..l10n import tr
from ..vocabulary import outcome_text
from .choice_store import ChoiceListsMixin
from .kinds import KindsMixin
from .device_texts import DeviceTextsMixin
from .master_data import MasterDataMixin
from .schema import _SCHEMA

SCHEMA_VERSION = 26


class SchemaMismatch(Exception):
    """The database file has another layout than this program."""


class CampaignClosed(Exception):
    """A change was attempted on a closed campaign."""


class ReadingIsFinal(Exception):
    """Something was about to change a measured value, its unit or its time."""


class DuplicateMeasurement(Exception):
    """A measurement from an instrument is already in the database."""


class Database(ChoiceListsMixin, KindsMixin, MasterDataMixin, DeviceTextsMixin):
    def __init__(self, path: Path | str):
        self.path = path
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        # SQLite's own LIKE folds ASCII only, which would miss "PRÜFUNG" vs "prüfung".
        self.connection.create_function(
            "fold", 1, lambda text: text.casefold() if isinstance(text, str) else text,
            deterministic=True,
        )
        # Readings are stored as measured; this is how they read, also in a search.
        self.connection.create_function("reading_text", 1, outcome_text, deterministic=True)
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self.connection.executescript(_SCHEMA)
            self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.connection.commit()
            self.seed_choice_lists()
            self.seed_kinds()
        elif version != SCHEMA_VERSION:
            self.connection.close()
            raise SchemaMismatch(tr(
                "The database has version {found}, this program needs version {needed}."
                " It has to be converted with an external tool first.",
                found=version, needed=SCHEMA_VERSION))
        # Readers keep working while a measurement is written, and a crash cannot
        # damage what was committed. Synchronous stays at FULL: a value that was
        # reported as saved has to survive a power cut.
        self.connection.execute("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        self.connection.close()

    def query(self, sql: str, *args) -> list[sqlite3.Row]:
        return self.connection.execute(sql, args).fetchall()

    def one(self, sql: str, *args) -> sqlite3.Row | None:
        return self.connection.execute(sql, args).fetchone()

    @contextmanager
    def transaction(self):
        try:
            with self.connection:
                yield self.connection
        except sqlite3.IntegrityError as err:
            if "campaign is closed" in str(err):
                raise CampaignClosed(str(err)) from err
            if "reading is final" in str(err):
                raise ReadingIsFinal(str(err)) from err
            if "measurement already stored" in str(err):
                raise DuplicateMeasurement(str(err)) from err
            raise

    def execute(self, sql: str, *args) -> int:
        with self.transaction() as connection:
            return connection.execute(sql, args).lastrowid
