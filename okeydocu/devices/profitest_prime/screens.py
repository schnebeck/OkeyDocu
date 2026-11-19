# OkeyDocu - okeydocu/devices/profitest_prime/screens.py
# The PROFITEST PRIME's measurement views by rotary switch position.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each view names the readings and what the five softkeys right of the display do, top to
bottom, as the instrument shows it at that position; `docs/profitest-prime-display.md` tells
the same in words. The labels are the instrument's own short ones. Where a key shows data of
the test point, a generic label or the element's own value stands for it. Once a reading
stands, the lowest softkey shares it."""

from __future__ import annotations

from ..screen import Key, Line, Path, Reading, Screen

SHARE_KEY = 4  # the softkey that shares a result, counted from 0
SHARE = Key(symbol="share")
LIMITS = Key(("Limits",))
TIME = Key(("ton:", "AUTO"))
OFFSET = Key(("ROFFSET", "ON|OFF"), "OFF")
RCD = Key(("{rated_residual_current}", "RCD", "{rcd_type}"))
DEVICE = Key(("IN", "gL/gG", "mm²"))  # the protective device and the cable behind it
Z_LIMITS = Key(("LIMITS", "UL", "IK"), "LIMITS")
SUPPLY = Line("U ---V   f ---Hz")
FREQUENCY = Line("f ---")
VIEWS = ("U", "U3~")


def path_key(count: str) -> Key:
    """The measuring path: its number of `count` and the way it is chosen."""
    return Key((count, "AUTO"), count)


def shared(screen: Screen) -> Screen:
    """The view once a reading stands."""
    return screen.with_key(SHARE_KEY, SHARE)


def _zloop(second: Key | None, paths: str = "01/09") -> Screen:
    return Screen("ZLOOP", (Reading("Z", "Ω"), Reading("IK", "A"), Path("L1-PE"), SUPPLY),
                  (DEVICE, second, Z_LIMITS, path_key(paths), None))


U = Screen("U", (None, Reading("U", "V"), Path("L1-PE"), FREQUENCY),
           (Key(VIEWS, "U"), None, None, path_key("01/10"), None))
U3 = Screen("U3~", (Reading("UL3-L1", "V"), Reading("UL1-L2", "V"), Reading("UL2-L3", "V"),
                    FREQUENCY),
            (Key(VIEWS, "U3~"), None, None, None, None))
RLO = Screen("RLO", (Reading("RLO", "Ω"), None, None, Line("ROFFSET 0,00Ω")),
             (TIME, Key(("POL", "→PE")), LIMITS, OFFSET, None))
RLO_25A = Screen("RLO 25A", (Reading("RLO", "Ω"), Reading("I", "A"), None, None),
                 (None, Key(("IHIGH",)), LIMITS, OFFSET, None))
RISO = Screen("RISO", (Reading("RISO", "Ω"), Reading("U", "V"), Path("N-PE"),
                       Reading("UISO", "V")),
              (TIME, Key(("500V", "UISO")), LIMITS, path_key("01/11"), None))
RCD_RAMP = Screen("RCD", (Reading("UIΔN", "V"), Reading("IΔ", "mA"), Reading("RE", "Ω"), SUPPLY),
                  (RCD, Key(("TN/TT",)), LIMITS, None, None))
RCD_TIME = Screen("RCD", (Reading("UIΔN", "V"), Reading("tA", "s"), Reading("RE", "Ω"), SUPPLY),
                  (RCD, Key(("1×IΔN", "TN/TT")), LIMITS, None, None))
RCD_BOTH = Screen("RCD", (Reading("UIΔN", "V"), Reading("tA", "s"), Reading("IΔ", "mA"),
                          Line("RE ---Ω")),
                  (None, RCD, LIMITS, None, None))
ZLOOP = _zloop(None)
ZLOOP_DC = _zloop(Key(("DC-L",)))
ZLOOP_HALF = _zloop(RCD, "01/03")
ZLOOP_PULSE = _zloop(RCD)
URES = Screen("Ures", (Reading("U", "V"), Reading("Ures", "V"), Reading("tU", "s"), FREQUENCY),
              (None, None, LIMITS, None, None))
IMD = Screen("IMD", (Reading("RL-PE", "MΩ"), Reading("tA", "s"), Line("Rmin   Rmax"), SUPPLY),
             (None, Key(("MAN±", "AUTO"), "MAN±"), Key(("RSTART", "50,0kΩ")),
              Key(("L1-PE", "±10,0%"), "L1-PE"), None))
RCM = Screen("RCM", (Reading("UIΔN", "V"), Reading("tA", "s"), Reading("IΔ", "mA"),
                     Line("RE ---Ω")),
             (None, Key(("IΔN", "½×IΔN")), LIMITS, None, None))
IL = Screen("IL", (Reading("IL", "A"), None, None, FREQUENCY),
            (None, None, LIMITS, None, None))
I_CLAMP = Screen("ILAMP", (Reading("IL/AMP", "A"), None, Path("100mV/mA"), None),
                 (Key(("I",)), Key(("SETTING", "V/A"), "SETTING"), LIMITS, None, None))
T_RH = Screen("T, r.H.", (Reading("T", "°C"), Reading("r.H.", "%"), None, None),
              (None, Key(("°C", "°F"), "°C"), None, None, None))
DELTA_U = Screen("ΔU", (Reading("ΔU", "%"), Reading("ZL-N", "Ω"), None, SUPPLY),
                 (Key(("ΔU",)), Key(("L1-N", "IN", "gL/gG")), LIMITS,
                  Key(("OFFSET", "ON|OFF"), "OFF"), None))

# By the value the instrument reports for the position; the view it opens with comes first.
AT_POSITION = {
    12: (U, U3), 13: (RLO,), 14: (RLO_25A,), 15: (RISO,), 17: (RCD_RAMP,), 18: (RCD_TIME,),
    19: (RCD_BOTH,), 20: (ZLOOP,), 21: (ZLOOP_DC,), 22: (ZLOOP_HALF,), 23: (ZLOOP_PULSE,),
    24: (URES,), 25: (IMD,), 26: (RCM,), 27: (IL,), 28: (I_CLAMP,), 29: (T_RH,), 30: (DELTA_U,),
}
