# EasyMeasurement - easymeasurement/store/master_data.py
# Customers, assets, people and templates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sqlite3

from ..l10n import tr


class MasterDataMixin:
    """What campaigns refer to: who, what and how it is reported."""

    # Master data ---------------------------------------------------------

    CUSTOMER_FIELDS = ("name", "street", "zip", "city", "comment")

    def add_customer(self, name: str, street="", zip="", city="", comment="") -> int:
        return self.execute(
            "INSERT INTO customers (name, street, zip, city, comment) VALUES (?, ?, ?, ?, ?)",
            name, street, zip, city, comment,
        )

    def update_customer(self, customer_id: int, **values: str) -> None:
        """Only the fields given change; unknown names are refused."""
        columns = [key for key in values if key in self.CUSTOMER_FIELDS]
        if len(columns) != len(values):
            raise ValueError(
                tr("Unknown customer fields: {fields}", fields=set(values) - set(columns)))
        self.execute(
            f"UPDATE customers SET {', '.join(f'{key}=?' for key in columns)} WHERE id=?",
            *(values[key] for key in columns), customer_id,
        )

    def add_asset(
        self, customer_id: int, kind: str, name: str, parent_id: int | None = None,
        identifier="", manufacturer="", type="", serial_no="", comment="", guid="",
    ) -> int:
        return self.execute(
            "INSERT INTO assets (customer_id, parent_id, kind, name, identifier, manufacturer,"
            " type, serial_no, comment, guid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            customer_id, parent_id, kind, name, identifier, manufacturer, type, serial_no, comment,
            guid,
        )

    def update_asset(
        self, asset_id: int, kind, name, identifier, manufacturer, type, serial_no, comment,
        basis="",
    ) -> None:
        self.execute(
            "UPDATE assets SET kind=?, name=?, identifier=?, manufacturer=?, type=?, serial_no=?,"
            " comment=?, basis=? WHERE id=?",
            kind, name, identifier, manufacturer, type, serial_no, comment, basis, asset_id,
        )

    def test_basis(self, asset_id: int | None) -> tuple[str, str]:
        """What the element is tested to: its own entry, and the one it follows, its own or
        that of the nearest element above that has one."""
        row = self.asset(asset_id) if asset_id is not None else None
        own, seen = (row["basis"] if row else ""), set()
        while row is not None and row["id"] not in seen:
            if row["basis"]:
                return own, row["basis"]
            seen.add(row["id"])
            row = self.asset(row["parent_id"]) if row["parent_id"] is not None else None
        return own, ""

    def customers(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM customers ORDER BY name COLLATE NOCASE")

    def assets(self, customer_id: int | None = None) -> list[sqlite3.Row]:
        if customer_id is None:
            return self.query("SELECT * FROM assets ORDER BY name COLLATE NOCASE")
        return self.query(
            "SELECT * FROM assets WHERE customer_id=? ORDER BY name COLLATE NOCASE", customer_id
        )

    def asset(self, asset_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM assets WHERE id=?", asset_id)

    def customer(self, customer_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM customers WHERE id=?", customer_id)

    # People --------------------------------------------------------------

    def users(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM users WHERE archived=0 ORDER BY name COLLATE NOCASE")

    def user(self, user_id: int | None) -> sqlite3.Row | None:
        return self.one("SELECT * FROM users WHERE id=?", user_id)

    def add_user(
        self, name: str, title: str = "", signature: bytes | None = None, certificate_path="",
        certificate_name="", certificate_until="",
    ) -> int:
        return self.execute(
            "INSERT INTO users (title, name, signature, certificate_path, certificate_name,"
            " certificate_until) VALUES (?, ?, ?, ?, ?, ?)",
            title, name, signature, certificate_path, certificate_name, certificate_until,
        )

    def update_user(
        self, user_id: int, name: str, title: str, signature: bytes | None, certificate_path: str,
        certificate_name: str, certificate_until: str,
    ) -> None:
        self.execute(
            "UPDATE users SET title=?, name=?, signature=?, certificate_path=?,"
            " certificate_name=?, certificate_until=? WHERE id=?",
            title, name, signature, certificate_path, certificate_name, certificate_until, user_id,
        )

    def remove_user(self, user_id: int) -> None:
        """Campaigns point to the people who did them, so those only leave the choice."""
        if self.one("SELECT 1 FROM campaigns WHERE user_id=?", user_id):
            self.execute("UPDATE users SET archived=1 WHERE id=?", user_id)
        else:
            self.execute("DELETE FROM users WHERE id=?", user_id)

    # Plans ---------------------------------------------------------------

    def plans(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM plans ORDER BY title COLLATE NOCASE")

    def save_plan(self, key: str, title: str, body: str) -> None:
        self.execute(
            "INSERT INTO plans (key, title, body, updated_at) VALUES (?, ?, ?, datetime('now'))"
            " ON CONFLICT(key) DO UPDATE SET title=excluded.title, body=excluded.body,"
            " updated_at=excluded.updated_at",
            key, title, body,
        )

    def delete_plan(self, key: str) -> None:
        self.execute("DELETE FROM plans WHERE key=?", key)

    # Templates -----------------------------------------------------------

    def templates(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM templates ORDER BY name COLLATE NOCASE")

    def save_template(self, name: str, body: str) -> None:
        self.execute(
            "INSERT INTO templates (name, body, updated_at) VALUES (?, ?, datetime('now'))"
            " ON CONFLICT(name) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
            name, body,
        )

    # The own firm -----------------------------------------------------------

    COMPANY_FIELDS = ("name", "street", "zip", "city", "phone", "email", "web", "logo")

    def company(self) -> dict[str, str]:
        """Empty texts until the firm is entered, so templates can always ask for it."""
        row = self.one("SELECT * FROM company WHERE id=1")
        return {key: (row[key] if row else "") for key in self.COMPANY_FIELDS}

    def save_company(self, **fields: str) -> None:
        values = {**self.company(), **fields}
        columns = ", ".join(self.COMPANY_FIELDS)
        self.execute(
            f"INSERT INTO company (id, {columns}) VALUES (1, {', '.join('?' * len(values))})"
            f" ON CONFLICT(id) DO UPDATE SET "
            + ", ".join(f"{key}=excluded.{key}" for key in self.COMPANY_FIELDS),
            *(values[key] for key in self.COMPANY_FIELDS),
        )
