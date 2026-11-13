# OkeyDocu - tests/test_secret_key.py
# The seal key in the password store: found, created, refused, unreachable, too slow.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import time
from contextlib import contextmanager

import pytest
from secretstorage.exceptions import SecretServiceNotAvailableException

from okeydocu.campaign.secret_key import ATTRIBUTES, SecretKeyStore

REAL_KEY_METHOD = SecretKeyStore.key


@pytest.fixture(autouse=True)
def real_key_method(monkeypatch):
    monkeypatch.setattr(SecretKeyStore, "key", REAL_KEY_METHOD)


class Item:
    def __init__(self, secret: bytes):
        self.secret = secret

    def get_secret(self) -> bytes:
        return self.secret


class Collection:
    """Stands in for the default collection of the Secret Service."""

    def __init__(self, stored: str = "", locked=False, dismissed=False, keeps=True):
        self.items = {}
        if stored:
            self.items[tuple(ATTRIBUTES.items())] = Item(stored.encode())
        self.locked, self.dismissed, self.keeps = locked, dismissed, keeps
        self.created = []

    def is_locked(self) -> bool:
        return self.locked

    def unlock(self, timeout=None) -> bool:
        self.locked = self.dismissed
        return self.dismissed

    def search_items(self, attributes):
        item = self.items.get(tuple(attributes.items()))
        return [item] if item else []

    def create_item(self, label, attributes, secret, replace=False):
        self.created.append(label)
        if self.keeps:
            self.items[tuple(attributes.items())] = Item(secret)


def store(collection, timeout=5):
    @contextmanager
    def opened():
        yield collection

    return SecretKeyStore(opened, timeout=timeout)


def test_key_is_created_in_the_store_on_first_use():
    collection = Collection()
    key = store(collection).key()
    assert len(key) == 32
    assert collection.search_items(ATTRIBUTES)[0].secret == key.hex().encode()


def test_stored_key_is_reused():
    collection = Collection("ab" * 32)
    assert store(collection).key() == bytes.fromhex("ab" * 32)
    assert collection.created == []


def test_a_locked_store_is_unlocked_first():
    collection = Collection("cd" * 32, locked=True)
    assert store(collection).key() == bytes.fromhex("cd" * 32)


def test_a_dismissed_unlock_means_no_key_and_no_new_one():
    collection = Collection(locked=True, dismissed=True)
    assert store(collection).key() is None
    assert collection.created == []


def test_a_store_that_cannot_be_reached_means_no_key():
    @contextmanager
    def missing():
        raise SecretServiceNotAvailableException("no Secret Service")
        yield

    assert SecretKeyStore(missing).key() is None


def test_a_store_that_does_not_answer_is_given_up_on():
    release = threading.Event()

    @contextmanager
    def hanging():
        release.wait(10)
        yield Collection("ab" * 32)

    started = time.monotonic()
    assert SecretKeyStore(hanging, timeout=0.2).key() is None
    assert time.monotonic() - started < 2
    release.set()


def test_key_that_cannot_be_read_back_is_not_used():
    assert store(Collection(keeps=False)).key() is None
