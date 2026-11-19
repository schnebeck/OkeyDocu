# PROFITEST PRIME: display and softkeys

What the instrument's display shows at each position of the rotary switch and which key
operates what. It was read from photographs of the display taken at every position from U to
the high-voltage step. The descriptions are in our own words; the instrument's own pictures
and texts are not reproduced.

## Keys around the display

Left of the display, top to bottom: ESC, MEM, HELP, ON/START (marked with a circled ▼) and
IΔN (marked with a circled I). They keep their meaning in every view.

Right of the display are five keys without printing: the softkeys `soft-1` to `soft-5`, top
to bottom. The display is divided into five rows of equal height, each beside one of them,
and shows what the key does in the view on screen. A row with only a bracket mark at the
edge is a key without function in that view.

## Kinds of views

**Measurement view.** A header row with the function symbol, the probes in use (PE, L, N),
the battery and the link symbol; below it the readings with their units and limits, at the
bottom voltage and frequency of the test point. The settings stand in the right-hand rows as
small boxes. The softkey beside a box changes that setting.

**Setting list.** A softkey of a setting opens it. The settings of the function stand in a
column on the left, the choices of the selected one in a column on the right; a counter such
as 1/1 or 2/2 at the top names the page. `soft-1` moves up, `soft-2` down, `soft-3` (→)
passes to the choices and back, `soft-4` (✓) takes the choice over. On the second page of the
RCD form list `soft-3` shows ↵ instead of →. The left column keeps the current values of all
settings of the function.

**Share.** Once a reading stands, `soft-5` shows the share symbol (an arrow into a box). It
sends the result over Push/Print. Without a reading the row is empty. This was seen in the
view U3~ with readings; the other views were photographed without readings.

**Help pages.** HELP shows pages for the function: the connection diagram with the operating
hint, then connections, display range, measuring range with operating uncertainty and nominal
values; some functions add error possibilities or a limit table. A counter at the bottom right
names the page.

**Prompt.** Switching ROFFSET on opens a prompt with two choices, ESC and CAL. They are taken
by the keys that carry the same symbols: ON/START for ESC, IΔN for CAL.

## Rotary switch positions

The switch has 24 positions, counted from OFF clockwise. The names are the dial's own; where
a position carries only a symbol, the function the display showed is named. `Value` is what
the instrument reports for the position (`SYS:GET:ROTATIONWHEEL`, a read command); it equals
the number here plus 11, and the driver's table in `selector.py` uses it.

| No | Value | Dial | Display shows |
|----|-------|------|---------------|
| 00 | 35 | OFF | |
| 01 | 12 | U | voltage between the probes, frequency; view U3~ |
| 02 | 13 | RLO 200 mA (0,2A) | resistance of the protective conductor |
| 03 | 14 | RLO 25 A | the same with 25 A |
| 04 | 15 | RISO, constant voltage | insulation resistance |
| 05 | 16 | RISO, rising voltage | voltage at which a surge protective device responds |
| 06 | 17 | RCD, IF ramp | touch voltage, tripping current, earth resistance |
| 07 | 18 | RCD, IΔN | touch voltage, tripping time, earth resistance |
| 08 | 19 | RCD, IF ramp and IΔN | all of the above together |
| 09 | 20 | ZLOOP AC | loop impedance, short-circuit current |
| 10 | 21 | ZLOOP DC (DC + sine) | the same with a DC component; variants DC-L and DC-H |
| 11 | 22 | ZLOOP, half-wave symbol | the same with an RCD in the circuit |
| 12 | 23 | ZLOOP, pulse symbol | the same with an RCD in the circuit |
| 13 | 24 | Ures | residual voltage after switching off, time window |
| 14 | 25 | IMD | insulation monitoring device in IT systems |
| 15 | 26 | RCM | residual current monitor: readings as at RCD, test current as a fraction of IΔN |
| 16 | 27 | IL | leakage current |
| 17 | 28 | ILAMP (≤1V=) | current with a clamp |
| 18 | 29 | T, %r.H. | temperature and humidity |
| 19 | 30 | Extra | voltage drop ΔU; the mode list also offers PRCD |
| 20 | 31 | no print | high voltage; the display says it is not installed |
| 21 | 32 | Auto | test sequences |
| 22 | 33 | Setup | |
| 23 | 34 | charging symbol | fast charge |

Positions 21 to 23 were not looked at. The driver calls positions 11 and 12 `ZLOOP+RLO` and
`ZLOOP+0.5x`; the display showed RCD data on `soft-2` at both.

## Softkeys per position

A dash means the row is empty.

| Position | soft-1 | soft-2 | soft-3 | soft-4 | soft-5 |
|----------|--------|--------|--------|--------|--------|
| 01 U view U | switch to U3~ | – | – | measuring path (AUTO) | – |
| 01 U view U3~ | switch to U | – | – | – | share |
| 02 RLO 200 mA | measuring time | polarity and target | limits | ROFFSET on/off | – |
| 03 RLO 25 A | – | IHIGH | limits | ROFFSET on/off | – |
| 04 RISO | measuring time | test voltage | limits | measuring path | – |
| 06 RCD IF ramp | RCD data | earthing system | limits | – | – |
| 07 RCD IΔN | RCD data | test current, earthing system | limits | – | – |
| 08 RCD IF and IΔN | – | RCD data | limits | – | – |
| 09 ZLOOP AC | protective device | – | limits | measuring path | – |
| 10 ZLOOP DC | protective device | DC variant | limits | measuring path | – |
| 11 ZLOOP half wave | protective device | RCD data | limits | measuring path | – |
| 12 ZLOOP pulse | protective device | RCD data | limits | measuring path | – |
| 13 Ures | – | – | limits | – | – |
| 14 IMD | – | mode MAN/AUTO | start resistance | path and tolerance | – |
| 15 RCM | – | test current | limits | – | – |
| 16 IL | – | – | limits | – | – |
| 17 ILAMP | clamp | clamp ratio | limits | – | – |
| 19 Extra | mode | path, protective device | limits | OFFSET on/off | – |

The share symbol on `soft-5` is shown only for U3~ because only there a reading was on the
display; it is expected in every view once a reading stands. In the RLO 25 A limit list the
key carries a table symbol and the label 60204-1 instead.

## What the settings offer

- **Measuring time:** AUTO, 1 min, 15 min.
- **Measuring path (U):** AUTO, which chooses the probes by itself, or one pair of line
  conductors, N and PE.
- **Measuring path (ZLOOP):** L1-PE, L2-PE, L3-PE, L1-N, L2-N, L3-N, L1-L2, L2-L3, L1-L3
  and AUTO. RISO has a list of the same kind; its view showed N-PE.
- **RLO limits:** below 0.10, 0.20, 0.30, 0.50, 1.00 Ω or a value entered by hand; at 25 A
  also a selection from the cable cross-section and the rated current of the protective
  device, after EN 60204-1.
- **RISO test voltage:** 50, 100, 250, 325, 500, 1000 V. Limits: above 50 kΩ up to above
  100 MΩ, or a value entered by hand.
- **RCD data:** rated residual current 6, 10, 30, 60, 100, 200, 300, 500, 1000 mA; type RCD,
  RCD-S, G/R, SRCD, PRCD-S, PRCD-K, RDC, RCMB; form A, F, B, B+ and further forms for
  charging stations; rated current 6 to 80 A and more.
- **RCD limits:** touch voltage below 25, 50 or 65 V; tripping time below 300 ms or above
  0 ms; tripping current above 15 mA, below 30 mA.
- **ZLOOP protective device:** rated current, characteristic, cable cross-section, cable type
  and number of cores; limits for the touch voltage (25, 50, 65 V) and the short-circuit
  current (2/3 Z, 3/4 Z, Ia).

## Open points

- The MAINS lamp was red in the photos at the RCD positions, at ZLOOP 11 and 12, at RCM and
  at Extra, and grey at U, RLO, RISO, ZLOOP 09 and 10, Ures, IMD, IL and ILAMP (positions
  looked at, not every photo). The meaning of the colours is not settled; the guides say the
  lamp lights up.
- The softkeys at positions 05 (rising voltage RISO) and 18 (T, %r.H.) are not known: only
  their setting lists and help pages were photographed.
