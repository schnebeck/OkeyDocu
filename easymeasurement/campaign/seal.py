# EasyMeasurement - easymeasurement/campaign/seal.py
# Seals a closed campaign, so that later changes to its data are noticed.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a seal can and cannot do.

The database refuses changes to a closed campaign, but anyone with the file can
remove those rules. So closing also computes a digest over everything recorded
and authenticates it with a key kept outside the database, in KWallet. Without
the key a valid seal cannot be made, even with full access to the file.

Each seal also contains the one before it, so a sealed campaign cannot vanish
from the middle unnoticed. The newest one could, which only something outside
this computer can reveal. That is why the seal is printed in the report, and a
signed report anchors it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

log = logging.getLogger(__name__)

WALLET_FOLDER = "EasyMeasurement"
WALLET_ENTRY = "seal-key"
DEFAULT_WALLET = "kdewallet"
WALLET_TIMEOUT_S = 60
_KEY_RE = re.compile(r"[0-9a-f]{64}")


class SealState(Enum):
    OPEN = "open"  # not closed yet, so nothing to check
    INTACT = "intact"  # data and seal agree, and the seal is genuine
    UNVERIFIED = "unverified"  # data and digest agree, the key was not available
    NOT_SEALED = "not_sealed"  # closed without a stored seal
    TAMPERED = "tampered"


@dataclass(frozen=True)
class SealCheck:
    state: SealState
    reasons: tuple[str, ...] = ()

    @property
    def rejected(self) -> bool:
        return self.state is SealState.TAMPERED


class KeyStore(Protocol):
    def key(self) -> bytes | None:
        """The key, created on first use. None if it cannot be reached."""


class KWalletKeyStore:
    def __init__(self, wallet: str = DEFAULT_WALLET):
        self._wallet = wallet

    def _run(self, *arguments: str, text: str | None = None) -> str | None:
        command = ["kwallet-query", "-f", WALLET_FOLDER, *arguments, self._wallet]
        try:
            result = subprocess.run(
                command, input=text, capture_output=True, text=True, timeout=WALLET_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as err:
            log.info("KWallet nicht erreichbar: %s", err)
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    def key(self) -> bytes | None:
        stored = self._run("-r", WALLET_ENTRY)
        if stored and _KEY_RE.fullmatch(stored):
            return bytes.fromhex(stored)
        created = secrets.token_hex(32)
        if self._run("-w", WALLET_ENTRY, text=created) is None:
            return None
        # Only a key that can be read back is worth sealing with.
        return bytes.fromhex(created) if self._run("-r", WALLET_ENTRY) == created else None


def _rows(db, sql: str, *arguments) -> list[dict]:
    return [dict(row) for row in db.query(sql, *arguments)]


def _without(row: dict, *columns: str) -> dict:
    return {key: value for key, value in row.items() if key not in columns}


def _photo_notes(db, photo: dict) -> None:
    """A photo's role and marks count where there are any, so older seals still hold."""
    if not photo["role"]:
        del photo["role"]
    marks = _rows(db, "SELECT number, x, y, w, h, text FROM photo_marks WHERE photo_id=?"
                      " ORDER BY number", photo["id"])
    if marks:
        photo["marks"] = marks


def _extras(db, campaign) -> dict:
    """What a campaign may hold beyond its readings. Only what is there enters the digest."""
    linked = (
        " LEFT JOIN measurements m ON m.id = {0}.measurement_id WHERE {0}.campaign_id=?"
        " ORDER BY {0}.sha256, {0}.id"
    )
    tables = {
        "photos": _rows(
            db, "SELECT p.*, m.device_uid FROM photos p" + linked.format("p"), campaign["id"]
        ),
        "attachments": _rows(
            db, "SELECT a.*, m.device_uid FROM attachments a" + linked.format("a"), campaign["id"]
        ),
        "photo_gaps": _rows(
            db, "SELECT * FROM photo_gaps WHERE campaign_id=? ORDER BY at, id", campaign["id"]
        ),
    }
    for photo in tables["photos"]:
        _photo_notes(db, photo)
    extras = {
        name: [_without(row, "id", "campaign_id", "measurement_id") for row in rows]
        for name, rows in tables.items() if rows
    }
    if campaign["photo_shift_s"]:
        extras["photo_shift_s"] = campaign["photo_shift_s"]
    if campaign["signature"]:
        extras["signature"] = hashlib.sha256(campaign["signature"]).hexdigest()
    return extras


def _run_of(db, measurement: dict) -> dict:
    """The run a measurement is a step of, and its hint. Only what is there enters the digest."""
    found = {}
    for column in ("step_name", "hint"):
        if measurement[column]:
            found[column] = measurement[column]
    if measurement["run_id"] is not None:
        run = db.one("SELECT * FROM runs WHERE id=?", measurement["run_id"])
        found["run"] = _without(dict(run), "id", "campaign_id")
    return found


def content(db, campaign_id: int, closed_at: str) -> bytes:
    """Everything a campaign recorded, in a fixed form. Database row numbers stay out."""
    campaign = db.one("SELECT * FROM campaigns WHERE id=?", campaign_id)
    measurements = []
    for row in _rows(db, "SELECT * FROM measurements WHERE campaign_id=? ORDER BY id", campaign_id):
        values = _rows(
            db, "SELECT * FROM measured_values WHERE measurement_id=? ORDER BY position, id",
            row["id"],
        )
        entry = {
            "measurement": _without(row, "id", "campaign_id", "step_id", "run_id", "step_name",
                                    "hint"),
            "values": [_without(value, "id", "measurement_id") for value in values],
        }
        entry.update(_run_of(db, row))
        measurements.append(entry)
    record = {
        "campaign": {
            key: campaign[key]
            for key in ("uuid", "asset_id", "plan_key", "plan_title", "title", "tester", "driver",
                        "device_json", "clock_offset_s", "started_at", "stored_since")
        },
        "closed_at": closed_at,
        "steps": [
            _without(row, "id", "campaign_id")
            for row in _rows(db, "SELECT * FROM steps WHERE campaign_id=? ORDER BY position", campaign_id)
        ],
        "clock": [
            _without(row, "id", "campaign_id")
            for row in _rows(db, "SELECT * FROM clock_checks WHERE campaign_id=? ORDER BY id", campaign_id)
        ],
        "changes": [
            _without(row, "id", "campaign_id", "measurement_id")
            for row in _rows(db, "SELECT * FROM measurement_log WHERE campaign_id=? ORDER BY id", campaign_id)
        ],
        "measurements": measurements,
    }
    record.update(_extras(db, campaign))
    return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def digest(db, campaign_id: int, closed_at: str) -> str:
    return hashlib.sha256(content(db, campaign_id, closed_at)).hexdigest()


def deletion_mark(moment: str) -> str:
    """Stands in for the previous seal when a deletion note is authenticated."""
    return f"deleted {moment}"


def authenticate(key: bytes, seal: str, previous: str) -> str:
    return hmac.new(key, f"{seal}:{previous}".encode(), hashlib.sha256).hexdigest()


def genuine(key: bytes, seal: str, previous: str, mac: str) -> bool:
    return hmac.compare_digest(authenticate(key, seal, previous), mac)
