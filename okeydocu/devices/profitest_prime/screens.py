# OkeyDocu - okeydocu/devices/profitest_prime/screens.py
# The PROFITEST PRIME's measurement views by rotary switch position.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each view names the readings and what the five softkeys right of the display do, top to
bottom, as the instrument shows it at that position; `docs/profitest-prime-display.md` tells
the same in words. A row a guide names as a setting has a name of its own here. The labels
are the instrument's own short ones. Where a key shows data of the test point, a generic label
or the element's own value stands for it. Once a reading stands, the lowest softkey shares
it."""

from __future__ import annotations

from ..screen import Key, Line, Path, Reading, Screen

SHARE = Key(symbol="share")
RESULT = (4, SHARE)  # the softkey that shares a result, counted from 0, and its row
LIMITS = Key(("Limits",))
TIME = Key(("ton:", "AUTO"))
SIGNAL = Key(("POL", "→PE"))  # the test signal: polarity, constant or ramp
OFFSET = Key(("ROFFSET", "ON|OFF"), "OFF")
RCD = Key(("{rated_residual_current}", "RCD", "{rcd_type}"))
TEST_CURRENT = Key(("1×IΔN", "TN/TT"))
EARTHING = Key(("TN/TT",))
TEST_VOLTAGE = Key(("500V", "UISO"))
CURRENT_LIMIT = Key(("ILIM", "1000µA"))
DC_VARIANT = Key(("DC-L",))
DEVICE = Key(("IN", "gL/gG", "mm²"))  # the protective device and the cable behind it
Z_LIMITS = Key(("LIMITS", "UL", "IK"), "LIMITS")
IMD_SEQUENCE = Key(("MAN±", "AUTO"), "MAN±")
IMD_START = Key(("RSTART", "50,0kΩ"))
IMD_PATH = Key(("L1-PE", "±10,0%"), "L1-PE")  # the conductor and the range the IMD may show
RCM_TEST = Key(("{rated_residual_current}", "½×IΔN"))
CLAMP_RATIO = Key(("SETTING", "V/A"), "SETTING")
EXTRA_MODE = Key(("ΔU",))  # the function chosen at the position Extra
DU_CIRCUIT = Key(("L1-N", "IN", "gL/gG"))
DU_OFFSET = Key(("OFFSET", "ON|OFF"), "OFF")
SUPPLY = Line("U ---V   f ---Hz", ("u_ln", "f"))
FREQUENCY = Line("f ---", ("f",))
EARTH = Line("RE ---Ω", ("re",))
# Readings several views share, each with the values of a result it shows.
VOLTS = Reading("U", "V", ("u", "u_lpe", "u_ln"))
LINE_VOLTS = (Reading("UL3-L1", "V", ("u_l3l1",)), Reading("UL1-L2", "V", ("u_l1l2",)),
              Reading("UL2-L3", "V", ("u_l2l3",)))
R_LOW = Reading("RLO", "Ω", ("rlo",))
TEST_VOLTS = Reading("UISO", "V", ("u_iso",))
TOUCH = Reading("UIΔN", "V", ("u_idn",))
TRIP_TIME = Reading("tA", "s", ("ta",))
TRIP_CURRENT = Reading("IΔ", "mA", ("i_f",))
EARTH_R = Reading("RE", "Ω", ("re",))
VIEW_U, VIEW_U3 = Key(("U", "U3~"), "U"), Key(("U", "U3~"), "U3~")


def path_key(count: str) -> Key:
    """The measuring path: its number of `count` and the way it is chosen."""
    return Key((count, "AUTO"), count)


U_PATH, RISO_PATH = path_key("01/10"), path_key("01/11")
Z_PATH, Z_PATH_RCD = path_key("01/09"), path_key("01/03")


def _zloop(second: Key | None, path: Key = Z_PATH) -> Screen:
    loop = Reading("Z", "Ω", ("zloop", "z_dc", "z_rlo", "z_half", "zlpe", "zln", "z"))
    return Screen("ZLOOP", (loop, Reading("IK", "A", ("ik",)), Path("L1-PE"), SUPPLY),
                  (DEVICE, second, Z_LIMITS, path, None))


U = Screen("U", (None, VOLTS, Path("L1-PE"), FREQUENCY),
           (VIEW_U, None, None, U_PATH, None))
U3 = Screen("U3~", (*LINE_VOLTS, FREQUENCY), (VIEW_U3, None, None, None, None))
RLO = Screen("RLO", (R_LOW, None, None, Line("ROFFSET 0,00Ω")),
             (TIME, SIGNAL, LIMITS, OFFSET, None))
RLO_25A = Screen("RLO 25A", (R_LOW, Reading("I", "A", ("i",)), None, None),
                 (None, Key(("IHIGH",)), LIMITS, OFFSET, None))
RISO = Screen("RISO", (Reading("RISO", "Ω", ("riso",)), VOLTS, Path("N-PE"), TEST_VOLTS),
              (TIME, TEST_VOLTAGE, LIMITS, RISO_PATH, None))
RISO_RAMP = Screen("RISO◢", (Line("UN"), VOLTS, Path("L1-PE"), TEST_VOLTS),
                   (CURRENT_LIMIT, TEST_VOLTAGE, LIMITS, RISO_PATH, None))
RCD_RAMP = Screen("RCD", (TOUCH, TRIP_CURRENT, EARTH_R, SUPPLY),
                  (RCD, EARTHING, LIMITS, None, None))
RCD_TIME = Screen("RCD", (TOUCH, TRIP_TIME, EARTH_R, SUPPLY),
                  (RCD, TEST_CURRENT, LIMITS, None, None))
RCD_BOTH = Screen("RCD", (TOUCH, TRIP_TIME, TRIP_CURRENT, EARTH),
                  (None, RCD, LIMITS, None, None))
ZLOOP = _zloop(None)
ZLOOP_DC = _zloop(DC_VARIANT)
ZLOOP_COMBINED = _zloop(RCD, Z_PATH_RCD)
ZLOOP_REDUCED = _zloop(RCD)
URES = Screen("Ures", (VOLTS, Reading("Ures", "V"), Reading("tU", "s"), FREQUENCY),
              (None, None, LIMITS, None, None))
IMD = Screen("IMD", (Reading("RL-PE", "MΩ"), TRIP_TIME, Line("Rmin   Rmax"), SUPPLY),
             (None, IMD_SEQUENCE, IMD_START, IMD_PATH, None))
RCM = Screen("RCM", (TOUCH, TRIP_TIME, TRIP_CURRENT, EARTH),
             (None, RCM_TEST, LIMITS, None, None))
IL = Screen("IL", (Reading("IL", "A", ("il",)), None, None, FREQUENCY),
            (None, None, LIMITS, None, None))
I_CLAMP = Screen("ILAMP", (Reading("IL/AMP", "A", ("i_clamp",)), None, Path("100mV/mA"), None),
                 (Key(("I",)), CLAMP_RATIO, LIMITS, None, None))
T_RH = Screen("T, r.H.", (Reading("T", "°C"), Reading("r.H.", "%"), None, None),
              (None, Key(("°C", "°F"), "°C"), None, None, None))
DELTA_U = Screen("ΔU", (Reading("ΔU", "%", ("u_delta",)), Reading("ZL-N", "Ω", ("zln",)), None,
                        SUPPLY),
                 (EXTRA_MODE, DU_CIRCUIT, LIMITS, DU_OFFSET, None))

# By the value the instrument reports for the position; the view it opens with comes first.
AT_POSITION = {
    12: (U, U3), 13: (RLO,), 14: (RLO_25A,), 15: (RISO,), 16: (RISO_RAMP,), 17: (RCD_RAMP,),
    18: (RCD_TIME,), 19: (RCD_BOTH,), 20: (ZLOOP,), 21: (ZLOOP_DC,), 22: (ZLOOP_COMBINED,),
    23: (ZLOOP_REDUCED,), 24: (URES,), 25: (IMD,), 26: (RCM,), 27: (IL,), 28: (I_CLAMP,),
    29: (T_RH,), 30: (DELTA_U,),
}
