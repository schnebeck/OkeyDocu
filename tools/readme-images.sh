#!/bin/bash
# OkeyDocu - tools/readme-images.sh
# Renders every picture of the README anew from invented data.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

# Usage: tools/readme-images.sh
#
# Needs the virtual environment of the project, the Breeze style, pngquant, pdftoppm and the
# Noto Sans fonts. Every picture shows invented data; what a run writes differs from the last
# one only in the times of day the program shows as "today".
set -eu
cd "$(dirname "$0")/.."
README_OUT=$(mktemp -d)
export README_OUT
trap 'rm -rf "$README_OUT"' EXIT
HERE=tools/readme_images

shoot() {  # language, then the scripts to run
    SHOT_LANG=$1
    export SHOT_LANG
    shift
    QT_STYLE_OVERRIDE=Breeze timeout 900 .venv/bin/python -m pytest "$@" -q \
        -p tests.conftest -p no:cacheprovider
}

# The photos are cut out of the pictures of the guide, so the guide comes first.
shoot en $HERE/shot_guide.py $HERE/shot_photos.py $HERE/shot_campaign.py $HERE/shot_report.py
shoot de $HERE/shot_campaign.py
timeout 300 .venv/bin/python $HERE/compose.py "$README_OUT" "$PWD"
echo "Pictures written to docs/images"
