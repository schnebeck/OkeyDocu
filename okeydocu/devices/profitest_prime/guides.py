# OkeyDocu - okeydocu/devices/profitest_prime/guides.py
# The PROFITEST PRIME's side of guided first measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every test lead fills all three sockets of its row. Plug and probe are marked differently:
plug 1 carries probe L (L1), plug 2 probe N (L3), plug 3 probe PE (L2); the conductor in
brackets is the one the lead takes for a phase sequence test. The softkeys are numbered from
the top of the column right of the display. A measurement is started with ON/START, the
fourth key left of the display, except the voltage, which the instrument measures as soon as
the probes are on; once a result stands, the lowest softkey shares it over Push/Print. A softkey is named only where its place is known from the instrument. The
measurements guided here run on the battery; one needing the mains says so at its supply.

The voltage follows the line conductors the element states: with three, the view U3~ measures
between L1, L2 and L3 first, then the leads move to L1, N and PE for the single voltages."""

from __future__ import annotations

from dataclasses import replace

from ...l10n import N_
from ..guide import CONFIGURE, CONNECT, MEASURE, PLACE, PREPARE, SELECT, Action, Guide, \
    Lead, Station, Variant

L_LEAD = ("1", "socket-1", "L (L1)")
N_LEAD = ("2", "socket-2", "N (L3)")
PE_LEAD = ("3", "socket-3", "PE (L2)")

STORE = Action(("soft-5",), N_("Press the share softkey at the bottom right: the instrument"
                                " prints the result to OkeyDocu and keeps nothing."))
BATTERY = (Action((), N_("The battery is enough for this measurement.")),
           Action(("mains-inlet", "mains-switch"),
                  N_("With a nearly empty battery plug the mains lead into the inlet at the top"
                     " right and switch on: 0 → I. The BAT symbol at the top of the display"
                     " shows how full the battery is.")))
MAINS = (Action(("mains-inlet", "mains-switch"), N_("This measurement needs the mains.")),
         Action((), N_("Plug the mains lead into the inlet at the top right and switch on:"
                       " 0 → I.")),
         Action(("led-mains",), N_("The MAINS lamp lights up.")))
SOFTKEYS = Action((), N_("Press the softkey beside a setting, choose the value with the arrow"
                         " keys, confirm it and take it over with ✓."))


def flow(supply=BATTERY) -> tuple[Station, ...]:
    """The PROFITEST PRIME's six stations; `supply` says what the instrument runs on."""
    return (Station(PLACE), Station(SELECT, N_("Rotary switch")), Station(CONNECT),
            Station(PREPARE, N_("Supply"), supply),
            Station(CONFIGURE, N_("Mode and limits"), (SOFTKEYS,), zoom=("lcd",)),
            Station(MEASURE))


LIMITS = N_("Limits: set them as the test basis requires.")
LIVE = (N_("Leave it switched on"), N_("The voltage is measured on the live supply."))
CONDUCTORS = ("line_conductors", "n_conductor")  # what reaches the test point

RCD_FEATURES = ("rcd_type", "rated_residual_current", "rated_current", "number_of_poles",
                "n_terminal")
LIVE_RCD = (
    (N_("Inform the operator"), N_("The test switches the circuit off.")),
    (N_("Secure the loads"), N_("Save data, stop running machines.")),
    (N_("Leave it switched on"), N_("The RCD and the circuit stay on.")),
)
RCD_TIME = Guide(
    "rcd_time", N_("RCD tripping test IΔN"), 18, "rcd", N_("RCD, outgoing side"),
    (Lead(*PE_LEAD, "pe", N_("Place probe PE (L2) on the PE bar.")),
     Lead(*L_LEAD, "out_l", N_("Place probe L (L1) on the outgoing line conductor terminal of"
                               " the RCD, usually an upper one.")),
     Lead(*N_LEAD, "out_n", N_("Place probe N (L3) on the outgoing N terminal of the RCD."))),
    N_("The test switches the circuit off. Secure the loads beforehand."),
    "rcd_type", RCD_FEATURES, True, LIVE_RCD, "IΔN",
    N_("Measures the touch voltage and the tripping time at the rated residual current."),
    settings=(
        Action(("soft-1",), N_("RCD: rated residual current IΔN, type and rated current IN,"
                               " as the RCD states them.")),
        Action(("soft-2",), N_("Test current: waveform, 1 × IΔN and the earthing system.")),
        Action(("soft-3",), LIMITS)),
    steps=(
        Action(("key-start",), N_("Press ON/START: the touch voltage is measured, the RCD"
                                  " does not trip yet.")),
        Action(("key-idn",), N_("Press IΔN: the RCD trips and the tripping time is"
                                " measured.")),
        STORE),
    results=("rcd_touch",), flow=flow())

LIVE_PARTS = N_("Live parts are exposed: touch only the grips of the probes.")
SWITCH = ("main_switch", N_("Main switch, incoming terminals"))
SINGLE = Guide(
    "u", N_("Voltage"), 12, *SWITCH,
    (Lead(*PE_LEAD, "pe", N_("Place probe PE (L2) on the PE bar.")),
     Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor L1.")),
     Lead(*N_LEAD, "in_n", N_("Place probe N (L3) on the incoming N, where there is one."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True, preparation=(LIVE,), selector_label="U",
    selector_note=N_("Measures the voltage between the probes and its frequency."),
    settings=(Action(("soft-4",), N_("Measuring path: AUTO measures L-PE, N-PE and L-N one"
                                     " after the other; without N choose L-PE.")),),
    steps=(Action((), N_("Hold the probes in place: the measurement starts by itself and the"
                         " voltage is shown at once.")), STORE),
    drawing_features=("nominal_voltage", "rated_current"), every_path=True, flow=flow())
AFTER_LINES = replace(
    SINGLE,
    settings=(Action(("soft-1",), N_("View: switch back to U with the top softkey.")),
              *SINGLE.settings),
    flow=(Station(CONNECT, N_("Leads to L1, N and PE")),
          Station(CONFIGURE, N_("Measuring path"), (SOFTKEYS,), zoom=("lcd",)),
          Station(MEASURE, N_("Single voltages"))))
THREE_PHASE = Guide(
    "u3", N_("Voltage and phase sequence"), 12, *SWITCH,
    (Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor L1.")),
     Lead(*PE_LEAD, "in_l2", N_("Place probe PE (L2) on the incoming line conductor L2.")),
     Lead(*N_LEAD, "in_l3", N_("Place probe N (L3) on the incoming line conductor L3."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True, preparation=(LIVE,), selector_label="U",
    selector_note=N_("Measures the voltage between the probes and its frequency."),
    settings=(Action(("soft-1",), N_("View: choose U3~ with its softkey. It shows the three"
                                     " voltages between the line conductors and the phase"
                                     " sequence.")),),
    steps=(Action((), N_("Hold the probes in place: the voltages and the phase sequence are"
                         " shown at once.")), STORE),
    drawing_features=("nominal_voltage", "rated_current"),
    flow=(Station(PLACE), Station(SELECT, N_("Rotary switch")),
          Station(CONNECT, N_("Leads to L1, L2 and L3")), Station(PREPARE, N_("Supply"), BATTERY),
          Station(CONFIGURE, N_("View U3~"), (SOFTKEYS,), zoom=("lcd",)),
          Station(MEASURE, N_("Line voltages"))),
    follow=AFTER_LINES)
VOLTAGE = replace(SINGLE, variants=(Variant(CONDUCTORS[0], "3", THREE_PHASE),))

PROTECTIVE_CONDUCTOR = Guide(
    "rlo", N_("Protective conductor resistance"), 13, "cee_plug",
    N_("CEE plug and housing of the machine"),
    (Lead(*L_LEAD, "pe_pin", N_("Place probe L (L1) on the PE contact of the CEE plug.")),
     Lead(*PE_LEAD, "body", N_("Place probe PE (L2) on a bare metal spot of the housing."))),
    N_("Measure only dead: the plug is pulled."),
    element_features=CONDUCTORS, live=False,
    preparation=((N_("Switch off and pull the plug"),
                  N_("The protective conductor is measured without voltage.")),
                 (N_("Find a bare metal spot"), N_("Paint and rust falsify the result."))),
    selector_label="RLO",
    selector_note=N_("Measures the resistance of the protective conductor with 200 mA."),
    settings=(Action(("soft-2",), N_("Polarity: both directions, the larger value counts.")),
              Action(("soft-3",), LIMITS),
              Action(("soft-4",), N_("With an extension lead: compensate it first (ROFFSET)."))),
    steps=(Action(("key-start",), N_("Press ON/START and hold the probes until the result"
                                     " stands.")), STORE),
    drawing_features=("rated_current",), flow=flow())

GUIDES = {guide.function: guide for guide in (RCD_TIME, VOLTAGE, PROTECTIVE_CONDUCTOR)}


def guide_for(function: str) -> Guide | None:
    return GUIDES.get(function)
