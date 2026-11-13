# OkeyDocu - okeydocu/store/choice_store.py
# Reading and writing choice lists: values, attributes, facts and methods in tables of their own.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from .choice_lists import ChoiceList, ChoiceValue, Method, shipped_choice_lists


class ChoiceListsMixin:
    """Lists are shared by every kind and customer; changing one changes every field using it."""

    def seed_choice_lists(self) -> None:
        for position, shipped in enumerate(shipped_choice_lists()):
            self.save_choice_list(shipped, position)

    def choice_lists(self) -> dict[str, ChoiceList]:
        """Every list by its key, in the order kept."""
        attributes: dict[str, list[str]] = {}
        for row in self.query("SELECT * FROM choice_attributes ORDER BY position, name"):
            attributes.setdefault(row["list"], []).append(row["name"])
        facts: dict[int, dict[str, str]] = {}
        for row in self.query("SELECT * FROM choice_facts"):
            facts.setdefault(row["value_id"], {})[row["attribute"]] = row["text"]
        methods: dict[int, list[Method]] = {}
        for row in self.query("SELECT * FROM choice_methods ORDER BY position, function"):
            methods.setdefault(row["value_id"], []).append(Method(row["function"], row["note"]))
        values: dict[str, list[ChoiceValue]] = {}
        for row in self.query("SELECT * FROM choice_values ORDER BY position, id"):
            values.setdefault(row["list"], []).append(ChoiceValue(
                row["value"], facts.get(row["id"], {}), row["help"], row["curve"],
                bytes(row["picture"] or b""), tuple(methods.get(row["id"], ()))))
        return {row["key"]: ChoiceList(row["key"], row["label"], row["help"],
                                       tuple(attributes.get(row["key"], ())),
                                       tuple(values.get(row["key"], ())))
                for row in self.query("SELECT * FROM choice_lists ORDER BY position, key")}

    def choice_list(self, key: str | None) -> ChoiceList | None:
        return self.choice_lists().get(key) if key else None

    def save_choice_list(self, chosen: ChoiceList, position: int | None = None) -> None:
        """Insert or replace the list with all its values."""
        if position is None:
            row = self.one("SELECT position FROM choice_lists WHERE key=?", chosen.key)
            position = row["position"] if row else self._next_list_position()
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO choice_lists (key, label, help, position) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET label=excluded.label, help=excluded.help,"
                " position=excluded.position",
                (chosen.key, chosen.label, chosen.help, position))
            connection.execute("DELETE FROM choice_attributes WHERE list=?", (chosen.key,))
            connection.execute("DELETE FROM choice_values WHERE list=?", (chosen.key,))
            connection.executemany(
                "INSERT INTO choice_attributes (list, name, position) VALUES (?, ?, ?)",
                [(chosen.key, name, number) for number, name in enumerate(chosen.attributes)])
            for number, entry in enumerate(chosen.values):
                value_id = connection.execute(
                    "INSERT INTO choice_values (list, value, position, help, curve, picture)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (chosen.key, entry.value, number, entry.help, entry.curve, entry.picture),
                ).lastrowid
                connection.executemany(
                    "INSERT INTO choice_facts (value_id, attribute, text) VALUES (?, ?, ?)",
                    [(value_id, name, text) for name, text in entry.facts.items() if text])
                connection.executemany(
                    "INSERT INTO choice_methods (value_id, function, note, position)"
                    " VALUES (?, ?, ?, ?)",
                    [(value_id, method.function, method.note, place)
                     for place, method in enumerate(entry.methods)])

    def _next_list_position(self) -> int:
        row = self.one("SELECT max(position) AS last FROM choice_lists")
        return (row["last"] or 0) + 1

    def choice_list_usage(self, key: str) -> int:
        """How many features of the kinds offer the list."""
        return self.one("SELECT count(*) AS n FROM kind_features WHERE choice_list=?", key)["n"]

    def delete_choice_list(self, key: str) -> None:
        """Features offering it become plain text fields; values noted with it stay."""
        with self.transaction() as connection:
            connection.execute("DELETE FROM choice_lists WHERE key=?", (key,))
