#!/bin/sh
# OkeyDocu - tools/install-desktop-entry.sh
# Puts OkeyDocu into the application menu of this user, started from this checkout.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The entry is named like the program reports itself to the desktop (okeydocu), so the
# window manager finds its icon and the task bar groups its windows. Run it again after the
# checkout has moved; `--remove` takes the entry away.
set -eu
cd "$(dirname "$0")/.."
here="$(pwd)"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
entry="$data/applications/okeydocu.desktop"
icon="$data/icons/hicolor/scalable/apps/okeydocu.svg"

if [ "${1:-}" = "--remove" ]; then
    rm -f "$entry" "$icon"
    echo "removed: $entry"
    exit 0
fi

mkdir -p "$(dirname "$entry")" "$(dirname "$icon")"
cp okeydocu/data/icons/okeydocu.svg "$icon"
cat > "$entry" <<EOF
[Desktop Entry]
Type=Application
Name=OkeyDocu
GenericName=Test reports
GenericName[de]=Prüfprotokolle
Comment=Guided measurement campaigns and test reports
Comment[de]=Geführte Messkampagnen und Prüfprotokolle
Exec="$here/.venv/bin/python" -m okeydocu
Path=$here
Icon=okeydocu
Terminal=false
Categories=Office;Engineering;
StartupWMClass=okeydocu
EOF
# A newer icon folder tells the icon caches of KDE and GTK to look again.
touch "$data/icons/hicolor"
if command -v update-desktop-database >/dev/null 2>&1; then
    timeout 20 update-desktop-database "$data/applications" || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    timeout 60 kbuildsycoca6 >/dev/null 2>&1 || true
fi
echo "installed: $entry"
