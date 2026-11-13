# OkeyDocu - okeydocu/ui/pinentry.py
# Asks for a key password through pinentry, the desktop's own secure password dialog.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""pinentry comes with GnuPG in a flavour for every desktop, pinentry-qt for Plasma. It locks
its memory and takes the keyboard; the password reaches the program only through the pipe of
the Assuan protocol: commands `SETDESC`, `GETPIN` and so on, each answered with `OK` or `ERR`,
the password as a `D` line, with `%`, carriage return and line feed written as `%XX`."""

from __future__ import annotations

import re
import shutil
import subprocess
import threading

PROGRAMS = ("pinentry-qt", "pinentry")
TIMEOUT_S = 120  # pinentry gives up by itself after this; the pipe is closed a little later
_ESCAPED = re.compile(r"%([0-9A-Fa-f]{2})")


def program() -> str | None:
    """The pinentry to use, or None where none is installed."""
    return next((found for name in PROGRAMS if (found := shutil.which(name))), None)


def available() -> bool:
    return program() is not None


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _unescape(text: str) -> str:
    return _ESCAPED.sub(lambda match: chr(int(match.group(1), 16)), text)


class _Session:
    def __init__(self, command: str):
        self.process = subprocess.Popen([command], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding="utf-8")
        self.guard = threading.Timer(TIMEOUT_S + 15, self.process.kill)
        self.guard.start()

    def reply(self) -> tuple[bool, str]:
        data = []
        for line in iter(self.process.stdout.readline, ""):
            line = line.rstrip("\n")
            if line.startswith("D "):
                data.append(_unescape(line[2:]))
            elif line.startswith("OK"):
                return True, "".join(data)
            elif line.startswith("ERR"):
                return False, line
        return False, "closed"

    def send(self, command: str, argument: str = "") -> tuple[bool, str]:
        line = f"{command} {_escape(argument)}" if argument else command
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()
        return self.reply()

    def close(self) -> None:
        self.guard.cancel()
        try:
            self.process.stdin.close()
            self.process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()


def ask(title: str, description: str, prompt: str, error: str = "", ok: str = "",
        cancel: str = "", command: str | None = None) -> str | None:
    """The password typed, or None if it was not given: cancelled, timed out, no pinentry."""
    command = command or program()
    if command is None:
        return None
    session = _Session(command)
    try:
        if not session.reply()[0]:
            return None
        for name, value in (("SETTITLE", title), ("SETDESC", description),
                            ("SETPROMPT", prompt), ("SETERROR", error), ("SETOK", ok),
                            ("SETCANCEL", cancel), ("SETTIMEOUT", str(TIMEOUT_S))):
            if value:
                session.send(name, value)
        given, password = session.send("GETPIN")
        return password if given else None
    except OSError:
        return None
    finally:
        session.close()
