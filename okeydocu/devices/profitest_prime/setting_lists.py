# OkeyDocu - okeydocu/devices/profitest_prime/setting_lists.py
# The setting lists of the PROFITEST PRIME, and the softkeys that switch its view.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A softkey beside a setting opens its list; a few softkeys switch the view instead. Each
list here holds what the instrument offers, in its order and its wording, where a picture of
the display is put into signs. The lists were read off the instrument's display. A list opens
on the page of the value in force, so the other page of a long list was not seen: it comes
from the list the instrument's software carries for that setting, wherever the page that was
seen agrees with it entry for entry. Where the two differ, the display stands and the unseen
page stays out (`before`, `of`). The test current of an RCD was not opened at the RCD tests:
its wave and its system stand as the residual current monitor lists them, its multiples and
the wave of the rising current as the software does. A setting that describes the test point
names the feature of the element that says which choice to take."""

from __future__ import annotations

from dataclasses import replace

from ..screen import Key, Screen, Setting, SettingList
from . import screens

PAIRS = ("L1-PE", "L2-PE", "L3-PE", "L1-N", "L2-N", "L3-N", "L1-L2", "L2-L3", "L1-L3")
BETWEEN_LINES = (*PAIRS[3:], "L-N")


def offered(name: str, values, unit: str) -> tuple[str, ...]:
    """The choices of one page, each worded as the list does: name, value and unit."""
    return tuple(f"{name} {value}{unit}" for value in values)


def only(*settings: Setting) -> SettingList:
    return SettingList(settings)


TIME = only(Setting("ton: AUTO", (("ton: AUTO", "ton: 1min", "ton: 15min"),)))
POLARITY = only(Setting("±POL→PE", (("±POL→PE", "+POL→PE", "-POL→PE",
                                     "±POL→◢", "+POL→◢", "-POL→◢"),)))
TEST_VOLTAGE = only(Setting("UN: 500V", (offered("UN:", (50, 100, 250, 325, 500, 1000), "V"),)))
LOW_LIMIT = only(Setting(
    "RLO <1,00Ω", (offered("RLO", ("<0,10", "<0,20", "<0,30", "<0,50", "<1,00"), "Ω"),),
    typed="<9,99Ω"))
HIGH_LIMIT = only(Setting(
    "R: >1,00MΩ", (offered("R:", (">50k", ">100k", ">500k", ">1,00M", ">2,00M", ">5,00M",
                                  ">7,00M", ">10,0M", ">70,0M"), "Ω"),),
    typed=">100MΩ"))
RAMP_CURRENT = only(Setting("I: 1000µA", (offered("I:", (5, 50, 500, 1000, 1250, 750), "µA"),)))
RAMP_LIMITS = only(Setting("U: >250V", typed=">250V"), Setting("U: <750V", typed="<750V"))

# The data of an RCD, as its softkey and that of the residual current monitor list them.
RESIDUAL = Setting("IΔN: {rated_residual_current}",
                   (offered("IΔN:", (6, 10, 30, 60, 100, 200, 300, 500, 1000), "mA"),),
                   feature="rated_residual_current")
FORM = Setting("{rcd_type}", (("A", "F", "B", "B+", "B - MI", "B+ - MI", "A - EV", "F - EV",
                               "RDC (6mA)", "RCMB"), ("F-audio", "AC")), feature="rcd_type")
RATED = Setting("IN: {rated_current}",
                (offered("IN:", (6, 10, 13, 16, 20, 25, 32, 40, 63, 80), "A"),
                 offered("IN:", (100, 125), "A")), feature="rated_current")
SYSTEM = Setting("TN/TT", (("TN/TT", "IT"),))
RCD_DATA = only(
    RESIDUAL,
    Setting("RCD", (("RCD", "RCD-S", "G/R (VSK)", "SRCD", "PRCD-S", "PRCD-K", "RDC", "RCMB"),)),
    FORM, RATED)
# A wave is a picture on the display: full wave by its angle, half wave, smooth current.
WAVES = ("0°: ∿", "180°: ∿", "NEG: ◡", "POS: ◠", "NEG: ⊔", "POS: ⊓")
WAVE = Setting(WAVES[0], (WAVES,))
TEST_CURRENT = only(WAVE, Setting("1×IΔN", (("½+1×IΔN", "1×IΔN", "2×IΔN", "5×IΔN"),)), SYSTEM)
RAMP_WAVE = only(Setting(WAVES[0], ((WAVES[0], *WAVES[2:4]),)), SYSTEM)
# The monitor's list strikes the last two forms of its first page out.
MONITOR = only(RESIDUAL, WAVE, Setting("½×IΔN", (("½×IΔN", "1×IΔN"),)),
               replace(FORM, pages=(FORM.pages[0][:8],), of=2), RATED, SYSTEM)

TOUCH = Setting("UL: <50V", (offered("UL:", ("<25", "<50", "<65"), "V"),))
SLOWEST, FASTEST = Setting("ta: <300ms", typed="<300ms"), Setting("ta: >0ms", typed=">0ms")
LEAST, MOST = Setting("IΔ:>15,0mA", typed=">15,0mA"), Setting("IΔ:<30,0mA", typed="<30,0mA")
LOOP_LIMITS = only(TOUCH, Setting(
    "IK: 2/3 Z", (offered("IK:", ("2/3 Z", "3/4 Z", "Ia", "Ia+Δ%"), ""),)))
LOOP_PATH = only(Setting("AUTO", ((*PAIRS, "AUTO"), ("L-N",))))
LOOP_PATH_RCD = only(Setting("AUTO", ((*PAIRS[:3], "AUTO"),)))
VOLTAGE_PATH = only(Setting("AUTO", ((*PAIRS[:3], "N-PE", *PAIRS[3:]), ("AUTO",))))
INSULATION_PATH = only(Setting(
    "AUTO", (("N-PE", *PAIRS[:3], "L+N-PE", *PAIRS[3:8]), (PAIRS[8], "AUTO"))))
DC_VARIANT = only(Setting("DC-L+", (("DC-L+", "DC-H+"),)))
RESIDUAL_LIMITS = only(Setting("Ulim: <60V", (("Ulim: <60V",),), typed="<50V"),
                       Setting("tU: <1s", (("tU: <1s", "tU: <5s"),), typed="<10s"))

# The protective device in front and the cable behind it.
FUSE = Setting("IN: 160A", (offered("IN:", ("2,0", "3,0", "4,0", "6,0", "8,0", 10, 13, 16, 20,
                                            25), "A"),
                            offered("IN:", (32, 35, 40, 50, 63, 80, 100, 125, 160), "A")))
CURVE = Setting("gL/G<0.2s TT", (
    ("2.5×IN (H)", "3×IN (A)", "5×IN (B)", "5×IN (L)", "6×IN (E)", "10×IN (C)", "10×IN (G)",
     "14×IN (K)", "20×IN (D)", "gL/gG <5s"),
    ("gL/G<0.4s TN", "gL/G<0.2s TT", "gL/gG <1s", "PKZM 6", "PKZM 8", "PKZM 10", "PKZM 12",
     "PKZM 14")))
SECTION = Setting("Ø: 70mm²", (offered("Ø:", (16, 25, 35, 50, 70), "mm²"),), before=1)
CABLE = Setting("H07V-K", (("2XFGY", "H05SJ-K", "H07BQ-F", "H07RN-F", "H07V-K", "H07V-U",
                            "NYIF-J", "NYM(N)", "NYM-J", "NYY"),), of=2)
CORES = Setting("1 -ADRIG", (tuple(f"{count} -ADRIG" for count in (1, 2, 3, 4, 5, 6, 7, 8,
                                                                    10)),))
DEVICE = only(FUSE, CURVE, SECTION, CABLE, CORES)
DROP_CIRCUIT = only(Setting("L1-N", (BETWEEN_LINES,)), FUSE, CURVE, SECTION, CABLE, CORES)

LEAKAGE_LIMIT = only(Setting(
    "IL: <50,0µA", (("IL: <50,0µA", "IL: <100µA", "IL: <500µA", "IL: <1,00mA", "IL: <2,00mA",
                     "IL: <5,00mA"),), typed="<10,0mA"))
CLAMP_RATIO = only(Setting(
    "100mV/mA", (("10V/A", "1V/A", "100mV/A", "10mV/A", "1mV/A", "100mV/mA"),)))
CLAMP_LIMITS = only(Setting("I: >0,10A", typed=">0,10A"), Setting("I: <10,0A", typed="<10,0A"))
MONITOR_PATH = only(Setting("L1-PE", (("L1-PE", "L2-PE"),)), Setting("± 10,0%", typed="10,0%"))
MONITOR_START = only(Setting(
    "R: 50,0kΩ", (offered("R:", ("60,0", "56,3", "53,1", "50,0", "47,3", "45,0", "42,5",
                                 "40,1", "37,9", "35,8"), "kΩ"),), of=7, before=4))

LOOP_VIEWS = (screens.ZLOOP, screens.ZLOOP_DC, screens.ZLOOP_COMBINED, screens.ZLOOP_REDUCED)

# By the view and the softkey row that opens the list.
LISTS: dict[tuple[Screen, Key], SettingList] = {
    (screens.U, screens.U_PATH): VOLTAGE_PATH,
    (screens.RLO, screens.TIME): TIME,
    (screens.RLO, screens.SIGNAL): POLARITY,
    (screens.RLO, screens.LIMITS): LOW_LIMIT,
    (screens.RLO_25A, screens.LIMITS): LOW_LIMIT,
    (screens.RISO, screens.TIME): TIME,
    (screens.RISO, screens.TEST_VOLTAGE): TEST_VOLTAGE,
    (screens.RISO, screens.LIMITS): HIGH_LIMIT,
    (screens.RISO, screens.RISO_PATH): INSULATION_PATH,
    (screens.RISO_RAMP, screens.CURRENT_LIMIT): RAMP_CURRENT,
    (screens.RISO_RAMP, screens.TEST_VOLTAGE): TEST_VOLTAGE,
    (screens.RISO_RAMP, screens.LIMITS): RAMP_LIMITS,
    (screens.RISO_RAMP, screens.RISO_PATH): INSULATION_PATH,
    (screens.RCD_RAMP, screens.RCD): RCD_DATA,
    (screens.RCD_RAMP, screens.EARTHING): RAMP_WAVE,
    (screens.RCD_RAMP, screens.LIMITS): only(TOUCH, LEAST, MOST),
    (screens.RCD_TIME, screens.RCD): RCD_DATA,
    (screens.RCD_TIME, screens.TEST_CURRENT): TEST_CURRENT,
    (screens.RCD_TIME, screens.LIMITS): only(TOUCH, SLOWEST, FASTEST),
    (screens.RCD_BOTH, screens.RCD): RCD_DATA,
    (screens.RCD_BOTH, screens.LIMITS): only(TOUCH, SLOWEST, FASTEST, LEAST, MOST),
    (screens.ZLOOP_DC, screens.DC_VARIANT): DC_VARIANT,
    (screens.ZLOOP_COMBINED, screens.Z_PATH_RCD): LOOP_PATH_RCD,
    (screens.ZLOOP_COMBINED, screens.RCD): RCD_DATA,
    (screens.ZLOOP_REDUCED, screens.RCD): RCD_DATA,
    (screens.URES, screens.LIMITS): RESIDUAL_LIMITS,
    (screens.IMD, screens.IMD_START): MONITOR_START,
    (screens.IMD, screens.IMD_PATH): MONITOR_PATH,
    (screens.RCM, screens.RCM_TEST): MONITOR,
    (screens.RCM, screens.LIMITS): only(TOUCH),
    (screens.IL, screens.LIMITS): LEAKAGE_LIMIT,
    (screens.I_CLAMP, screens.CLAMP_RATIO): CLAMP_RATIO,
    (screens.I_CLAMP, screens.LIMITS): CLAMP_LIMITS,
    (screens.DELTA_U, screens.DU_CIRCUIT): DROP_CIRCUIT,
    **{(view, screens.DEVICE): DEVICE for view in LOOP_VIEWS},
    **{(view, screens.Z_LIMITS): LOOP_LIMITS for view in LOOP_VIEWS},
    **{(view, screens.Z_PATH): LOOP_PATH for view in LOOP_VIEWS
       if view.softkey(screens.Z_PATH) is not None},
}


def _two_way(view: Screen, key: Key, choice: str) -> dict[tuple[Screen, Key], Screen]:
    """A softkey row with two halves: a press puts the other half, `choice`, in force. The
    view with that half in force keeps the lists of `view`."""
    other = replace(key, inverted=choice)
    there = view.with_key(view.softkey(key), other)
    LISTS.update({(there, row): LISTS[view, row] for row in there.keys if (view, row) in LISTS})
    return {(view, key): there, (there, other): view}


# By the view and the softkey row pressed: the view the softkey switches to at once.
SWITCHES: dict[tuple[Screen, Key], Screen] = {
    (screens.U, screens.VIEW_U): screens.U3,
    (screens.U3, screens.VIEW_U3): screens.U,
    **_two_way(screens.T_RH, screens.T_RH.keys[1], "°F"),
    **_two_way(screens.IMD, screens.IMD_SEQUENCE, "AUTO"),
}


def setting_list(view, key) -> SettingList | None:
    """The list the softkey row `key` opens in `view`, where it is known."""
    return LISTS.get((view, key))


def softkey_view(view, key) -> Screen | None:
    """The view the softkey row `key` of `view` switches to, where it switches one."""
    return SWITCHES.get((view, key))
