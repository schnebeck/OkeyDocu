# OkeyDocu - okeydocu/devices/profitest_prime/setting_lists.py
# The setting lists of the PROFITEST PRIME: what each softkey of a setting offers.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A softkey beside a setting opens its list. Each list here is read off the instrument's
display and holds what it offers, in its order and its wording; a list or a page that was not
seen is left out rather than guessed. A setting that describes the test point names the
feature of the element that says which choice to take."""

from __future__ import annotations

from ..screen import Setting, SettingList
from . import screens

PAIRS = ("L1-PE", "L2-PE", "L3-PE", "L1-N", "L2-N", "L3-N", "L1-L2", "L2-L3", "L1-L3")


def offered(name: str, values, unit: str) -> tuple[str, ...]:
    """The choices of one page, each worded as the list does: name, value and unit."""
    return tuple(f"{name} {value}{unit}" for value in values)


TIME = SettingList((Setting("ton: AUTO", (("ton: AUTO", "ton: 1min", "ton: 15min"),)),))
TEST_VOLTAGE = SettingList((Setting(
    "UN: 500V", (offered("UN:", (50, 100, 250, 325, 500, 1000), "V"),)),))
LOW_LIMIT = SettingList((Setting(
    "RLO <1,00Ω", (offered("RLO", ("<0,10", "<0,20", "<0,30", "<0,50", "<1,00"), "Ω"),),
    typed="<9,99Ω"),))
HIGH_LIMIT = SettingList((Setting(
    "R: >1,00MΩ", (offered("R:", (">50k", ">100k", ">500k", ">1,00M", ">2,00M", ">5,00M",
                                  ">7,00M", ">10,0M", ">70,0M"), "Ω"),),
    typed=">100MΩ"),))
RAMP_CURRENT = SettingList((Setting(
    "I: 1000µA", (offered("I:", (5, 50, 500, 1000, 1250, 750), "µA"),)),))
RAMP_LIMITS = SettingList((Setting("U: >250V", typed=">250V"),
                           Setting("U: <750V", typed="<750V")))
RCD_DATA = SettingList((
    Setting("IΔN: {rated_residual_current}",
            (offered("IΔN:", (6, 10, 30, 60, 100, 200, 300, 500, 1000), "mA"),),
            feature="rated_residual_current"),
    Setting("RCD", (("RCD", "RCD-S", "G/R (VSK)", "SRCD", "PRCD-S", "PRCD-K", "RDC", "RCMB"),)),
    Setting("{rcd_type}", (("A", "F", "B", "B+", "B - MI", "B+ - MI", "A - EV", "F - EV",
                            "RDC (6mA)", "RCMB"), ("F-audio", "AC")), feature="rcd_type"),
    Setting("IN: {rated_current}",
            (offered("IN:", (6, 10, 13, 16, 20, 25, 32, 40, 63, 80), "A"),),
            feature="rated_current", of=2),
))
TOUCH = Setting("UL: <50V", (offered("UL:", ("<25", "<50", "<65"), "V"),))
SLOWEST, FASTEST = Setting("ta: <300ms", typed="<300ms"), Setting("ta: >0ms", typed=">0ms")
LEAST, MOST = Setting("IΔ:>15,0mA", typed=">15,0mA"), Setting("IΔ:<30,0mA", typed="<30,0mA")
LOOP_LIMITS = SettingList((TOUCH, Setting(
    "IK: 2/3 Z", (offered("IK:", ("2/3 Z", "3/4 Z", "Ia", "Ia+Δ%"), ""),))))
LOOP_PATH = SettingList((Setting("AUTO", ((*PAIRS, "AUTO"),), of=2),))
LOOP_PATH_RCD = SettingList((Setting("AUTO", ((*PAIRS[:3], "AUTO"),)),))
VOLTAGE_PATH = SettingList((Setting(
    "AUTO", ((*PAIRS[:3], "N-PE", *PAIRS[3:]), ("AUTO",))),))
DC_VARIANT = SettingList((Setting("DC-L+", (("DC-L+", "DC-H+"),)),))
RESIDUAL_LIMITS = SettingList((Setting("Ulim: <60V", (("Ulim: <60V",),), typed="<50V"),
                               Setting("tU: <1s", (("tU: <1s", "tU: <5s"),), typed="<10s")))

LOOP_VIEWS = (screens.ZLOOP, screens.ZLOOP_DC, screens.ZLOOP_COMBINED, screens.ZLOOP_REDUCED)

# By the view and the softkey row that opens the list.
LISTS: dict[tuple, SettingList] = {
    (screens.U, screens.U_PATH): VOLTAGE_PATH,
    (screens.RLO, screens.TIME): TIME,
    (screens.RLO, screens.LIMITS): LOW_LIMIT,
    (screens.RLO_25A, screens.LIMITS): LOW_LIMIT,
    (screens.RISO, screens.TIME): TIME,
    (screens.RISO, screens.TEST_VOLTAGE): TEST_VOLTAGE,
    (screens.RISO, screens.LIMITS): HIGH_LIMIT,
    (screens.RISO_RAMP, screens.CURRENT_LIMIT): RAMP_CURRENT,
    (screens.RISO_RAMP, screens.TEST_VOLTAGE): TEST_VOLTAGE,
    (screens.RISO_RAMP, screens.LIMITS): RAMP_LIMITS,
    (screens.RCD_RAMP, screens.RCD): RCD_DATA,
    (screens.RCD_RAMP, screens.LIMITS): SettingList((TOUCH, LEAST, MOST)),
    (screens.RCD_TIME, screens.RCD): RCD_DATA,
    (screens.RCD_TIME, screens.LIMITS): SettingList((TOUCH, SLOWEST, FASTEST)),
    (screens.RCD_BOTH, screens.RCD): RCD_DATA,
    (screens.RCD_BOTH, screens.LIMITS): SettingList((TOUCH, SLOWEST, FASTEST, LEAST, MOST)),
    (screens.ZLOOP_DC, screens.DC_VARIANT): DC_VARIANT,
    (screens.ZLOOP_COMBINED, screens.Z_PATH_RCD): LOOP_PATH_RCD,
    (screens.URES, screens.LIMITS): RESIDUAL_LIMITS,
    **{(view, screens.Z_LIMITS): LOOP_LIMITS for view in LOOP_VIEWS},
    **{(view, screens.Z_PATH): LOOP_PATH for view in LOOP_VIEWS
       if view.softkey(screens.Z_PATH) is not None},
}


def setting_list(view, key) -> SettingList | None:
    """The list the softkey row `key` opens in `view`, where it is known."""
    return LISTS.get((view, key))
