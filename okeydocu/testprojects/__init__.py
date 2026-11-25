# OkeyDocu - okeydocu/testprojects/__init__.py
# Test projects: the program on invented data of its own, to try it with.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A test project is the program on data of its own, made up and ready to play with: started
with `--testproject <name>`, the program works in a folder of that name below its data and
never touches the real records. The project is laid out on the first start and kept from then
on; `--fresh` begins it anew.

    prime   a machine and its parts, two campaigns under way, and a PROFITEST PRIME without
            hardware: panel, dial, guides and setting lists, with random readings"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..paths import data_dir

PROJECTS = ("prime",)


def folder(name: str) -> Path:
    """Where the data of the test project live, below the program's own."""
    return data_dir() / "testprojects" / name


def enter(name: str, fresh: bool = False) -> Path:
    """Points the program at the test project's data. To be called before anything opens the
    database; `fresh` throws the project away first."""
    if name not in PROJECTS:
        raise ValueError(name)
    target = folder(name)
    if fresh and target.exists():
        shutil.rmtree(target)
    os.environ["OKEYDOCU_DATA"] = str(target)
    return target


def prepare(context, name: str) -> None:
    """Brings what the project needs beside its data, and lays the data out where there are
    none yet."""
    from . import prime

    {"prime": prime.prepare}[name](context)
