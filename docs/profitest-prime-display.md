# PROFITEST PRIME: display and softkeys

What the instrument's display shows at each position of the rotary switch and which key
operates what. It was read from photographs of the display taken at every position from U to
the high-voltage step; what a setting or a lamp means comes from the maker's operating
instructions (PROFITEST PRIME, document 3-349-933). The descriptions are in our own words; the
instrument's own pictures and texts are not reproduced.

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

**Share.** Once a reading stands, `soft-5` shows the share symbol (three dots joined like a
"<") in a frame. It sends the result over Push/Print. Without a connection to the laptop the
same key shows the save symbol and stores the result in the instrument's memory. Without a
reading the row is empty. This was seen in the
view U3~ with readings; the operating instructions say the same of every function: a result
can be stored by softkey after a successful measurement.

**Help pages.** HELP shows pages for the function: the connection diagram with the operating
hint, then connections, display range, measuring range with operating uncertainty and nominal
values; some functions add error possibilities or a limit table. A counter at the bottom right
names the page.

**Prompt.** Switching ROFFSET on opens a prompt with two choices, ESC and CAL. They are taken
by the keys that carry the same symbols: ON/START for ESC, IΔN for CAL. ROFFSET is meant for
extension leads only, the instrument's own leads need no compensation: with the extension
short-circuited, IΔN measures its resistance, which is then subtracted from every result.

## Lamps

MAINS NETZ tells of the voltage at the probes, not of the instrument's own supply. At the
positions that need the mains at the test point (RCD, ZLOOP, IMD, RCM, ΔU):

| Lamp | Meaning |
|------|---------|
| green | connected correctly, mains voltage there, measurement released |
| green, flashing | probe N not connected, measurement released |
| yellow | 65 to 253 V against PE from two line conductors, a system without N, released |
| yellow, flashing | probes L and N are both on line conductors |
| red, flashing | no mains voltage, PE interrupted, or the RCD has tripped |

At RLO, RISO, IL and ILAMP a steady red means a voltage at the test point: the measurement is
blocked. At U the lamp has no meaning. The instrument's own mains supply shows in the red glow
lamp of its mains switch; BATT is yellow on the battery, flashes green while charging and
is green when full.

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
| 09 | 20 | ZLOOP AC | loop impedance, short-circuit current; an RCD in front may trip |
| 10 | 21 | ZLOOP DC (DC + sine) | made for circuits behind an RCD of type A or F, which it should not trip: half waves with a DC component, DC-L faster, DC-H safer |
| 11 | 22 | ZLOOP, half-wave symbol | the same for type A, F or B: L-N with full current, N-PE with a reduced one |
| 12 | 23 | ZLOOP, pulse symbol | the same for type A or F: a test current reduced after the RCD's data |
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

Positions 21 to 23 were not looked at.

### Loop impedance: four positions, four ways

The dial marks them with signs under one arc. The instrument's help names the probes and the
range it states an accuracy for; the firmware names the positions as the driver does.

| No. | Value | Driver's name | Sign on the dial | Probes | Range |
|---|---|---|---|---|---|
| 09 | 20 | `ZLOOP` | sine | 1(L), 3(PE) | 50 mΩ to 5 Ω |
| 10 | 21 | `ZLOOP+DC` | DC+ and a sine | 1(L), 2(N), 3(PE) | 250 mΩ to 5 Ω |
| 11 | 22 | `ZLOOP+RLO` | sine with a bar | 1(L) on L, 2(N) on PE, 3(PE) on N | 0,5 to 99,9 Ω |
| 12 | 23 | `ZLOOP+0.5x` | square pulses | 1(L), 3(PE) | 10 to 999 Ω |

Position 09 trips an RCD in front. Position 10 saturates it with a direct current first and
needs N at the test point. Position 11 measures L-N with the full current and N-PE with a small
one; its help carries a warning sign because the probes N and PE change places. Position 12
keeps the test current small enough for the RCD set and reads coarsely. The display showed RCD
data on `soft-2` at positions 11 and 12, the DC variant at position 10.

## Softkeys per position

A dash means the row is empty.

| Position | soft-1 | soft-2 | soft-3 | soft-4 | soft-5 |
|----------|--------|--------|--------|--------|--------|
| 01 U view U | switch to U3~ | – | – | measuring path (AUTO) | – |
| 01 U view U3~ | switch to U | – | – | – | share |
| 02 RLO 200 mA | measuring time | test signal | limits | ROFFSET on/off | – |
| 03 RLO 25 A | – | IHIGH | limits | ROFFSET on/off | – |
| 04 RISO | measuring time | test voltage | limits | measuring path | – |
| 05 RISO, rising voltage | current limit | test voltage | limits | measuring path | – |
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
| 18 T, %r.H. | – | unit °C or °F | – | – | – |
| 19 Extra | mode | path, protective device | limits | OFFSET on/off | – |

The share symbol on `soft-5` is seen in the views U3~ and U, each with a reading on the
display; it is expected in every view once a reading stands. In the RLO 25 A limit list the
key carries a table symbol and the label 60204-1 instead.

## What the settings offer

- **Measuring time:** AUTO ends the measurement once the value is taken, holding ON/START
  goes on measuring; 1 min and 15 min run that long.
- **Test signal (RLO):** the polarity, positive, negative or both in turn, each as a constant
  current or as a ramp.
- **Measuring path (U):** the view U measures between the probes L and PE only. The path names
  the two conductors they are on, for the record; the instrument switches nothing. Set by
  hand, every reading is stored for that pair. With AUTO the instrument names the pairs one
  after the other and moves on with each reading stored, IΔN skips a pair: L1-PE, L2-PE,
  L3-PE, N-PE, L1-N, L2-N, L3-N, L1-L2, L2-L3, L1-L3. RISO and ZLOOP run through their pairs
  the same way.
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

- **IMD:** the sequence is MAN or AUTO, the start resistance RSTART lies between 15 kΩ and
  2,5 MΩ, the path is L1-PE or L2-PE with a range in percent the monitor's own reading has to
  lie in. Probes 1(L) on L1, 2(N) on L2, 3(PE) on PE. ON/START switches the resistance in and
  starts a stop watch; with MAN two softkeys with a rising and a falling ramp change the
  resistance, with AUTO it changes every 2 s; IΔN changes the conductor; ON/START again stops
  when the monitor raises its alarm. The response is then rated with a check mark or a cross,
  and only a rated result can be stored.
- **RCM:** rated residual current 10 to 1000 mA, waveform, the factor ½ × IΔN or 1 × IΔN,
  type, rated current, earthing system; limit for the touch voltage. Probes 1(L) and 3(PE)
  on the load side of the transformer, 2(N) as well for direct current. ON/START measures
  the touch voltage; IΔN sends the test current: at half the rated residual current no alarm
  may come within 10 s, at the full one IΔN is pressed again when the alarm comes, which
  stops the time. The response is rated as at the IMD.
- **IL:** limits from 50 µA to 5 mA or entered by hand. Probe 3(PE) on the protective
  conductor, probe 1(L) on the conductive part; the current is measured through 2 kΩ, on and
  on. The part has to be free of voltage: above 60 V the instrument switches off.
- **ILAMP:** the clamp has a round socket of its own, 1 V at most. The ratio has to be set as
  the clamp's switch stands (10 V/A to 1 mV/A, 100 mV/mA for the leakage current clamp).
  Around the protective conductor alone it measures the leakage current, around the line
  conductors and N together the residual current.
- **Extra, ΔU:** `soft-1` chooses the function; the circuit is a pair L-N or two line
  conductors with the rated current and characteristic of the fuse in front; the limit is a
  percentage. Probes 1(L) and 3(PE) on that pair. With OFFSET the line impedance at the
  handover point is measured once (IΔN, a prompt, IΔN again) and left out of the readings
  that follow.

## In the application

The views are kept in `okeydocu/devices/profitest_prime/screens.py`, one per position and
view, and drawn on the panel's display in the guided measurement. A row that shows data of the
test point on the instrument, such as the RCD's rated residual current or the protective
device, carries the element's own value or a generic label there; limits are left out, because
they are settings.

The row of position 05 is taken from the picture of that view in the operating instructions;
it was not photographed.
