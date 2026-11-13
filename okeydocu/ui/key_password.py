# OkeyDocu - okeydocu/ui/key_password.py
# The password of a signing key, asked for through pinentry where it is installed.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A key without a password is used as it is. Otherwise pinentry asks, up to three times, and
says what was wrong the time before; the window stays answering while it waits. Without
pinentry the password typed into the form is taken instead."""

from __future__ import annotations

from ..l10n import tr
from ..reporting.sign import SigningError, certificate_info, needs_password
from . import pinentry
from .common import run_busy

TRIES = 3


def password_for(parent, reference: str, typed: str = "") -> str:
    """The password that opens the key named by `reference`; SigningError if none does."""
    if not pinentry.available():
        return typed
    if not needs_password(reference):
        return ""
    error = ""
    for _ in range(TRIES):
        given = run_busy(parent, tr("Waiting for the password …"), lambda: pinentry.ask(
            tr("Sign report"), tr("The password of the signing key is needed."),
            tr("Password:"), error, tr("Sign"), tr("Cancel")))
        if given is None:
            raise SigningError(tr("Signing was cancelled."))
        try:
            certificate_info(reference, given)
        except SigningError as err:
            error = str(err)
            continue
        return given
    raise SigningError(error)
