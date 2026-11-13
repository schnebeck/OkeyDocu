#!/bin/sh
# OkeyDocu - tools/setup-venv.sh
# Builds an isolated .venv. Only PySide6 comes from the distribution, because it must
# match the system Qt for the Plasma style to load; everything else is pinned here.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
cd "$(dirname "$0")/.."

system_site=$(/usr/bin/python3 -I -c 'import PySide6, pathlib; print(pathlib.Path(PySide6.__file__).parents[1])') || {
    echo "PySide6 fehlt: bitte das Distributionspaket python3-pyside6 installieren." >&2
    exit 1
}

rm -rf .venv
/usr/bin/python3 -m venv .venv
venv_site=$(.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')
for package in PySide6 shiboken6; do
    ln -s "$system_site/$package" "$venv_site/$package"
done

.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pip install --quiet --no-deps --no-build-isolation -e .
.venv/bin/python -c 'import PySide6.QtWidgets, okeydocu; print("venv bereit")'
