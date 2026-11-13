# EasyMeasurement - easymeasurement/devices/profitest_prime/mapping.py
# The PROFITEST PRIME's codes in the application's vocabulary: the one place that knows them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument names everything by text ids (TSnnnn) that follow its translation file.

What is mapped here becomes a key of the vocabulary. Everything else keeps its code and is
named, when shown, from the instrument's own texts in the current language; without them
the code is shown. Nothing is guessed.
"""
from __future__ import annotations

import re
from importlib import resources

from ...l10n import current

CODE = re.compile(r"^TS\d{4}$")

FUNCTIONS = {
    "TS1165": "riso",
    "TS1178": "i_clamp",
    "TS1285": "rlo",
    "TS1286": "u",
    "TS1287": "zln_du",
    "TS1289": "il",
    "TS1290": "imd",
    "TS1291": "ures",
    "TS1292": "i_ramp",
    "TS1294": "rcm_touch",
    "TS1296": "rcd_touch",
    "TS1297": "rcd_time",
    "TS1298": "rcd_ramp_touch",
    "TS1299": "rcd_current",
    "TS1417": "rlo_25a",
    "TS1607": "zloop",
    "TS1608": "zloop_dc",
    "TS1609": "zloop_rlo",
    "TS1610": "zloop_half",
    "TS1611": "riso_ramp",
}

RESULTS = {
    "TS1159": "rotation",
    "TS1165": "riso",
    "TS1170": "u_iso",
    "TS1178": "i_clamp",
    "TS1286": "u",
    "TS1289": "il",
    "TS1348": "u_idn",
    "TS1349": "ta",
    "TS1350": "u_ln",
    "TS1351": "f",
    "TS1352": "re",
    "TS1353": "i_f",
    "TS1354": "zlpe",
    "TS1355": "ik",
    "TS1356": "zln",
    "TS1357": "ue",
    "TS1358": "rlo",
    "TS1359": "rlo_delta",
    "TS1360": "rlo_plus",
    "TS1361": "rlo_minus",
    "TS1362": "rlo_offset",
    "TS1363": "u_lpe",
    "TS1364": "u_npe",
    "TS1365": "i",
    "TS1369": "u_delta",
    "TS1371": "u_l3l1",
    "TS1372": "u_l1l2",
    "TS1373": "u_l2l3",
    "TS1632": "zloop",
    "TS1633": "z_dc",
    "TS1634": "z_rlo",
    "TS1635": "z_half",
    "TS1655": "z",
}

# Outcomes of a VERIFICATION, stored as the vocabulary's neutral words.
OUTCOMES = {"TS1181": "left", "TS1182": "right", "TS1183": "error"}

# Which conductors a measurement was taken between. Every function has its own setting.
CONDUCTOR_SETTINGS = {"TS1225", "TS1245", "TS1261", "TS1264", "TS1274", "TS1275"}
CONDUCTORS = {
    "TS1326": "L-N",
    "TS1328": "AUTO",
    "TS1435": "L1-PE",
    "TS1436": "L2-PE",
    "TS1437": "L3-PE",
    "TS1438": "N-PE",
    "TS1439": "L+N-PE",
    "TS1440": "L1-N",
    "TS1441": "L2-N",
    "TS1442": "L3-N",
    "TS1443": "L1-L2",
    "TS1444": "L2-L3",
    "TS1445": "L1-L3",
}

# Settings the vocabulary knows; they are held against the element they were set for.
SETTINGS = {"TS1228": "rated_residual_current", "TS1230": "rated_current", "TS1238": "rcd_type"}

# The program's languages onto the instrument's; one it lacks falls back to English.
CULTURES = {"de": "de-DE", "en": "en-GB", "es": "es-ES"}
FALLBACK_CULTURE = "en-GB"


def function_key(code: str) -> str:
    return FUNCTIONS.get(code, code)


def result_key(code: str) -> str:
    return RESULTS.get(code, code)


def outcome(code: str) -> str:
    return OUTCOMES.get(code, code)


def is_conductor_setting(code: str) -> bool:
    return code in CONDUCTOR_SETTINGS


def setting_key(code: str) -> str:
    return SETTINGS.get(code, code)


def conductor(code: str) -> str:
    return CONDUCTORS.get(code, code)


def is_code(text: str) -> bool:
    return bool(CODE.match(text or ""))


def instruction_folder():
    """How the instrument is set up and connected for each function."""
    return resources.files(__package__) / "instructions"


def culture() -> str:
    """The instrument's language that matches the current one."""
    return CULTURES.get(current(), FALLBACK_CULTURE)
