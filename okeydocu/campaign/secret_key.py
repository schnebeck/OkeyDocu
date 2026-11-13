# OkeyDocu - okeydocu/campaign/secret_key.py
# The seal key in the desktop's password store, through the freedesktop Secret Service.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The key is one item of the default collection, found by its attributes. KWallet, GNOME
Keyring and KeePassXC all serve this interface. The whole access runs in a worker thread with
a time limit: a locked store asks for its password, and nobody may be there to give it."""

from __future__ import annotations

import logging
import secrets
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager

import secretstorage
from secretstorage.exceptions import SecretStorageException

from .seal import KEY_PATTERN

log = logging.getLogger(__name__)

ATTRIBUTES = {"application": "OkeyDocu", "entry": "seal-key"}
LABEL = "OkeyDocu seal key"
TIMEOUT_S = 60


@contextmanager
def default_collection():
    """The desktop's default collection, on a connection of its own."""
    bus = secretstorage.dbus_init()
    try:
        yield secretstorage.get_default_collection(bus)
    finally:
        bus.close()


def _stored(collection) -> list[str]:
    return [item.get_secret().decode("ascii", "replace")
            for item in collection.search_items(ATTRIBUTES)]


class SecretKeyStore:
    def __init__(self, collection: Callable[[], AbstractContextManager] = default_collection,
                 timeout: float = TIMEOUT_S):
        self._collection = collection
        self._timeout = timeout

    def key(self) -> bytes | None:
        """The key, created on first use. None if the store cannot be reached in time."""
        found: list[bytes | None] = []
        worker = threading.Thread(target=lambda: found.append(self._fetch()), daemon=True)
        worker.start()
        worker.join(self._timeout)
        if worker.is_alive():
            log.info("Password store did not answer within %s s", self._timeout)
            return None
        return found[0] if found else None

    def _fetch(self) -> bytes | None:
        try:
            with self._collection() as collection:
                return self._key_in(collection)
        except (SecretStorageException, TimeoutError, OSError) as err:
            log.info("Password store not reachable: %s", err)
            return None

    def _key_in(self, collection) -> bytes | None:
        # unlock() is True when the person dismissed the request.
        if collection.is_locked() and collection.unlock(timeout=self._timeout):
            return None
        for stored in _stored(collection):
            if KEY_PATTERN.fullmatch(stored):
                return bytes.fromhex(stored)
        created = secrets.token_hex(32)
        collection.create_item(LABEL, ATTRIBUTES, created.encode("ascii"), replace=True)
        # Only a key that can be read back is worth sealing with.
        return bytes.fromhex(created) if created in _stored(collection) else None
