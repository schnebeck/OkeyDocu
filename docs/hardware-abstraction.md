# Hardware abstraction

EasyMeasurement does not know any instrument. It knows a vocabulary of measuring functions,
results, quantities, outcomes and settings, and every instrument is translated into that
vocabulary before the application sees its data. An instrument that measures something new,
such as sound level at a machine, brings its words into the vocabulary and needs no change in
the user interface, the store or the reports.

## Three layers

```
 instrument ──► driver ──► mapping ──► app vocabulary ──► store, UI, reports
              (protocol)  (codes→keys)   (keys, names)
```

1. **Driver** (`easymeasurement/devices/<instrument>/`): transport, protocol, events and the
   instrument's own texts. It implements `MeterDriver` from `devices/base.py` and declares what
   it can do in `capabilities`. It reads the instrument's records in the instrument's terms.
2. **Mapping** (`devices/<instrument>/mapping.py`): the one place where the instrument's codes
   appear. It turns a function code into a function key, a result code into a result key, an
   outcome code into a neutral word, a known setting into a setting key. The instrument's own
   record is stored unchanged with every measurement (`raw`), so the origin of each figure can
   always be traced. What the mapping does not know is passed through as the instrument's code
   and named by the instrument itself (see below).
3. **App vocabulary** (`easymeasurement/vocabulary/`, data in `data/vocabulary/<domain>.yaml`):
   keys, symbols, units and English names. The program's language catalogues translate the
   names (`data/languages/<code>/vocabulary_<domain>.yaml`). Plans, templates, the store and the
   reports use only these keys.

The application never reads an instrument's texts directly. When it has to name a code the
mapping did not know, it asks `devices/naming.py`, which asks the drivers that registered
`InstrumentWords`: the driver says which texts are its codes and which of its languages matches
the program's, and the texts stored when the instrument was set up give the name.

## The vocabulary

A domain file lists what one field of measurement needs:

```yaml
# data/vocabulary/electrical.yaml (excerpt)
quantities:
  resistance: {unit: Ω, name: Resistance}
  voltage: {unit: V, name: Voltage}
results:
  rlo: {symbol: RLO, quantity: resistance, name: Protective conductor resistance}
  u_ln: {symbol: ULN, quantity: voltage, name: Line voltage L-N}
functions:
  rlo: {symbol: RLO, name: Protective conductor resistance}
outcomes:
  right: {name: right}
settings:
  conductor: {name: Conductor}
```

- **Quantity**: what is measured, with its unit. `Quantity.parse` uses the units of all
  quantities to understand prefixes (`mΩ`, `kHz`); the text as the instrument sent it is always
  kept as `raw` and is what reports print.
- **Result**: one figure a function produces, with its symbol and quantity.
- **Function**: a measuring function as the inspector chooses it; plans and the step editor list
  these. Its label is `symbol – name`. It may list the results it produces (`results`).
- **Outcome**: the neutral word of a check without a number (rotating field `right`), stored as
  that word so a report can print it in any language.
- **Setting**: a known setting of a function, such as the conductors a value was taken between.

Keys are stable: they are stored with every measurement. Names and symbols may change at any
time, and a language may write a symbol its own way (`I_CLAMP` is `I_ZANGE` in German). Two
files may not define the same key, and a field the loader does not know is refused, so an
unquoted comma in a name cannot go unnoticed.

## Passing unknown codes through

An instrument can always send more than its mapping knows: a new firmware, a rarely used
function, one of fifty settings. Nothing is guessed. The value keeps the instrument's code as its
key and is named from the instrument's own texts (for the PROFITEST PRIME its translation file,
read once when the instrument is set up). Without those texts the code is shown. Once such a code
turns out to matter, it gets a key in the vocabulary and a line in the mapping; measurements taken
before keep the code they were stored with.

## Adding an instrument: a sound level meter

The example is a hand-held sound level meter that sends a line per stored reading over a USB
serial port, such as `LEQ,A,F,78.4,2026-05-04T10:15:02`.

1. **Vocabulary.** Acoustics is a new field, so it gets `data/vocabulary/acoustics.yaml`:

   ```yaml
   quantities:
     sound_pressure_level: {unit: dB, name: Sound pressure level}
   results:
     laeq: {symbol: LAeq, quantity: sound_pressure_level, name: Equivalent continuous level (A)}
     lafmax: {symbol: LAFmax, quantity: sound_pressure_level, name: Maximum level (A, fast)}
     lcpeak: {symbol: LCpeak, quantity: sound_pressure_level, name: Peak level (C)}
   functions:
     sound_level: {symbol: Lp, name: Sound level at a workplace, results: [laeq, lafmax, lcpeak]}
   settings:
     frequency_weighting: {name: Frequency weighting}
     time_weighting: {name: Time weighting}
   ```

   The German names go into `data/languages/de/vocabulary_acoustics.yaml`
   (`Sound pressure level: Schalldruckpegel`, …). The l10n test fails until every name has one.
2. **Driver package** `easymeasurement/devices/sound_meter/`:
   - `discovery.py` finds the instrument (USB vendor and product id) and returns
     `FoundInstrument` entries; the operator never sees ports.
   - `transport.py` owns the serial port, with a timeout on every read and an allowlist of the
     commands the program may send. Commands are taken from the manufacturer's reference, never
     tried out on the instrument.
   - `driver.py` implements `MeterDriver`: `identify`, `read_clock`, `read_measurements` and,
     if the instrument pushes readings, `subscribe_live`. Capabilities say which of these work.
   - `mapping.py` turns `LEQ`/`A` into result `laeq`, `MAX`/`A`/`F` into `lafmax` and the
     weighting letters into the settings `frequency_weighting` and `time_weighting`. Everything
     else passes through. The line as received is kept as the measurement's `raw`.
3. **Description.** `devices/sound_meter/info.py` describes the driver as a `DriverInfo`
   (`devices/driver_info.py`), and `_load_builtin()` in `devices/registry.py` registers it.
   Only key, label and factory are needed. The others, where they apply:
   - `find`: lists the instruments that can be chosen now;
   - `words`: an `InstrumentWords`, if the instrument names its own codes;
   - `instructions`: its folder of instructions;
   - `pairing`: a `Pairing` for a wireless instrument that is paired once (button text,
     steps on the instrument, default PIN, and the function that pairs and returns the port);
   - `preparing`: what the operator is told while the program gets the instrument ready;
   - `simulated`: for a software instrument whose readings may never be signed.

   The application asks the registry (`driver_info`, `available_drivers`, `is_simulated`) and
   never imports a driver package. Texts in the description are English source texts; their
   translations go into `data/languages/<code>/<driver>.yaml`.
4. **Instructions.** How to set up and connect the instrument for a function lives with the
   driver: `devices/sound_meter/instructions/sound_level.yaml`, in the same form as the
   PROFITEST PRIME's (`devices/profitest_prime/instructions/`). They are written in English;
   their words go into each language's `instructions.yaml` catalogue, and the l10n test fails
   until every one has a German entry.
5. **Plans and limits.** A plan step with function `sound_level` and an upper limit of 80 dB
   works like any other step: the guided measurement waits for a reading of that function, the
   verdict comes from the limit, the report prints the results with their symbols.
6. **Tests.** A test per layer with invented frames: the transport refuses commands outside its
   list, the mapping turns sample lines into the expected keys and keeps unknown tokens, the
   driver delivers `MeterMeasurement`s through a fake port. No test needs the instrument.

Nothing in `ui/`, `store/`, `campaign/` or `reporting/` changes for a new instrument.

## Checklist

- Device codes appear only in `devices/<instrument>/mapping.py`.
- Nothing outside `devices/` imports a driver package; the application asks the registry.
  Two places know a driver by design: the UI drives the simulator itself (demos, test runs of
  a plan), and the IZYTRON import reads results a PROFITEST PRIME took, with its mapping.
- The instrument's record is kept as `raw`; an unknown code stays the key.
- New keys exist in `data/vocabulary/`, new names in every language catalogue.
- Only commands from the instrument's documented reference are sent, through an allowlist.
- Every blocking call has a timeout; every loop over instrument data has an end.
- Tests use invented data only.
