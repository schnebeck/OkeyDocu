# Architecture

## Data model

    customers ─< assets (tree of elements, kind from asset_kinds) ─ kind_features
                   └─< campaigns ─< measurements ─< measured_values
                          └─< reports

| Term | Meaning |
|---|---|
| Campaign | One inspection appointment at an installation. It is the unit from which a report is made. |
| Measurement | One operation with a point in time, a function and a verdict. It has 0 to n measured values. |
| Measured value | `kind` is `number`, `text` or `photo`. |

Numbers are stored twice: `raw` is the text of the instrument and is printed unchanged,
`base_value` and `base_unit` serve for comparing and filtering (`2.05MΩ` becomes
2050000 Ω). A value filter stays within its unit.

Every instrument measurement keeps its origin: the record of the instrument (`raw_data`), serial number,
firmware, time of arrival at the PC with time zone. The GUID of an instrument occurs only once in the
whole database.

The program does not migrate databases. It creates a new database in the current schema and
rejects any other schema version at start. A required conversion runs beforehand with an external
tool.

A photo is attached as a measured value to the measurement it belongs to. If it cannot be assigned
unambiguously, it becomes a measurement of its own with the function `foto`. Such photos do not count
towards the overall result.

## Structure

The structure of a customer is a tree of any depth (`assets`), freely nestable as in
IZYTRON. The kinds of the elements are in `asset_kinds`, their features in `kind_features`; both can be
changed under Settings → Structure kinds (`ui/kinds_page.py`). The kinds from `data/kinds.yaml` are
supplied. Every kind names its IZYTRON kind code for the import and a test interval. Feature values are
collected at the element (`features_json`); empty ones are not stored and are shown nowhere. When a
kind is deleted, its elements get a substitute kind, and their values stay stored invisibly.
A feature can offer a choice list (`kind_features.choice_list`); the element form then shows
it as a choice field that also accepts other values. A choice list is a small table in
the database: values are rows (`choice_values`), properties are columns (`choice_attributes`), a
fact is a cell (`choice_facts`). A value also carries a help text, a characteristic curve
(`breaker 3 5`: range of instantaneous tripping in multiples of Iₙ), an image of its own, such as
the characteristic curve from a data sheet, and the suitable measuring functions with a hint
(`choice_methods`). Several features share one list, “Supply cable” for example that of the cable types.
A new database starts with `data/choice_lists.yaml`, `data/kinds.yaml` assigns the features to the
lists; they are edited under Settings → Choice lists (`ui/choice_lists_page.py`).
Supplied texts are stored in English in the database and translated through the catalogues; the
facts are checked against two independent sources each.

The tooltip of a value (`ui/choice_tips.py`) names only the properties in which the values
of the list differ: for B, C, D “Circuit breaker” is left out, next to fuses it is
there. A characteristic curve is drawn for the element: its rated current turns multiples into amperes, its
system type together with the rated current gives the required disconnection time, at which Iₐ is marked. The tooltip
itself is a general component (`ui/rich_tip.py`) for text, table and images that any
widget can use through `install_tip`. F1 in the choice field sets all values of the list side by side in these
properties, the chosen one in bold; the field takes the key before the shortcut of the
window. The system type is usually given at the machine or supply:
if it is missing at the element, the one of the next element above applies (`ui/suited_methods.py`).

In the campaign the side panel shows the chosen element (`ui/place_panel.py`) with the same
tooltips at its features. Below it are the suitable measurements, collected from the values
of all features; the tooltip of a measurement names the values that call for it, with their hints.
So at an unfamiliar machine one sees what can be measured at an element. “Cores of the cable” counts all cores of a cable like the
core count of the PROFITEST PRIME (NYM-J 5×2.5: 5, a single core: 1), “Poles of the protective device”
states whether one, two, three or four poles are switched.

Every element has a test basis (`basis`). When empty, it follows that of the element above; the top
one needs one, and the form says so as long as it is missing. The report names it in the title (“Test report
to …”), and an element with a different one of its own names it in its card.
In the report the language files translate kinds and features through their key (`kinds`,
`features`), not through the German name: the German word “Leiter” is a ladder as a kind and a
conductor in a measured value. Kinds and features created by the user stay German.

A measurement is attached to an element (`asset_id`); its location in the report is the path to it. Rebooking,
renaming and moving rewrite this path in open campaigns (`campaign/structure.py`);
sealed measurements stay where they are, and an element they are attached to cannot be
deleted. A push of the instrument brings no location; it lands at the element chosen in the tree. A fetch
from the instrument memory brings the instrument path; missing elements are created as measuring points.

An inspection becomes due when, since the closing of the last campaign at an element, its
interval (its own or that of the kind) has run out, 30 days in advance. A closed campaign
with defects waits for a follow-up until a campaign refers to it through `follows_id`
(`campaign/due.py`). The overview shows both under “Due”.

## What is fixed about a measurement

Measured value, unit and timestamp are final. Database triggers enforce this, not only the
user interface. The offset of the instrument clock may recompute `local_time`; `device_time` stays.

Function, measuring location, inspector, comment and verdict can be overwritten, and per measured value
designation, limits and verdict (`EDITABLE_FIELDS`). Correcting texts and deleting duplicate measurements is
everyday work and leaves no note. Of a deleted measurement only the identifier remains, so that it
does not come back on a fetch. Changes to function, verdict and limits, in contrast, are recorded with
old and new value in `measurement_log`, which can only be appended to. In the report
such measurements are marked “changed” and those entered by hand “manual”.

## Open and closed

A campaign is open, also after an import, and can be revised. A report is made
only from a closed campaign, so at that point at the latest it is closed. Before that a
draft (`drafts/entwurf.pdf`, with the notice “DRAFT”, not archived) shows what it would look like.
“Confirm” closes, seals, files the PDF and signs in one step. The certificate
is checked beforehand; if something fails after that, the record stays sealed and the report can
be made later under “Reports”.

Closing seals the record (`campaign/seal.py`): a SHA-256 sum is formed over all contents
and authenticated with a key from KWallet (HMAC). Every seal contains the
previous one. Master data are not part of it; a renamed customer is no manipulation. Before every
report and every signature the seal is checked; a modified record is rejected.

Limits: whoever has the key can forge a seal. The disappearance of the latest campaign
does not show in the chain. That is why the seal is printed in the report: a signed report
anchors it outside this computer. If the key is lost, the data can still be checked
against the sum, but their authenticity cannot.

## Closed campaigns

Database triggers prevent any change to measurements, measured values and steps of a
closed campaign, also when bypassing the program. Reports are made only from closed
campaigns. A signature creates a new archive entry; the original is kept.

## The 0/1/n problem in templates

A template is a list of blocks. A `measurements` block does not fix how many
measurements there are, but describes three presentations between which the data decide:

| Data | Presentation |
|---|---|
| 0 | Sentence with a reason, or the block is left out (`none: {hide: true}`) |
| 1 | Form with designation and value |
| n | Table with min and max row |

Measurements of different functions do not share a table, because their columns do not
fit together; each function is counted on its own. The min/max comparison runs over
`base_value`; the original text is shown.

A measurement block first names what its measurements have in common: settings of the instrument,
measuring conditions such as the R_LO offset, and limits. The table below shows per measurement only what
differs, and what was measured (`reporting/measurement_table.py`). Values that only count for a
failed measurement get a column only in that case. Measured values are shown as number and
unit with a prefix in steps of a thousand (p, n, µ, m, k, M, G, T), such as `220 mΩ`; only
the decimal point is moved, never rounded. Quantity symbols are italic with an upright subscript index.

Remarks belong in the row of their measurement: comment, notes, attachments and references to photos
are listed one below the other in the column “Remark”. Photos are numbered through the report (`[3]`);
the remark refers to them, with the notice number if the photo is marked (“see note 1 in
[3]”). The PDF places every photo like a footnote on the page of the row that names it, with the
list of notices below: at most three side by side and two rows per page
(`reporting/pdf_photos.py`).

The block `structure` orders the measurements along the structure tree of the installation. With `order: place`
every element with measurements is a section with its features and within it one block per measured
quantity; with `order: function` every measured quantity appears once, with what all its elements share,
and below it per element only what differs from that. Steps of a plan without a measurement follow with
their reason. The standard template uses `order: place`. With `layout: compact` every element has
a single table over all measurement types in the order of the measurements, with measurement type, result,
limit and remark; what the measurements of one measurement type share at the element is stated once above it. The
template “Standard report, compact” uses it. Every element shows below its heading what
it is as a test object: identifier, manufacturer, type, features and its remark.

At the foot, location, date and name are already on the lines (`fills` of the block `signature`): the seat
of the own company, the creation date and the inspector, whose stored signature replaces the
name. The digital signature comes after that.

`resolve()` turns template and data into document nodes, `render_pdf()` makes the PDF from them.
Placeholders run in a Jinja sandbox, so that a template cannot reach program internals.

The report language is independent of the program language and is stored with the report.
`reporting/language.py` holds it during generation; every text is looked up through its German
original in `data/languages/<code>.yaml`, and anything missing stays German. Measured values
are never rounded; only the decimal separator and spacing follow the language. Notes and attachments on
measurements are shown with them, those on locations in the block `attachments`.

The overall result does not overstate: a skipped or empty step gives “Not completely
tested”, never “Passed”.

## Languages

All texts are in English in the code and are looked up when shown: `tr("Serial number
{serial}", serial=…)`, counted with `plural()`, module constants marked with `N_()` and translated where
they appear (`easymeasurement/l10n/`). Every language has a folder under `data/languages/<code>/`:
`language.yaml` with names and formats for date, time and decimal separator, next to it catalogue files per
area with `texts` (English → language) and `contexts` for an English word that needs two
translations. A text may appear in several files, but only with the same translation.

The program language is chosen under “Settings → Language” and applies from the next start;
“As the system” takes the system language at every start. The notice below it appears in the
language currently chosen. Only languages with `program: true` are offered; the others serve
reports. `speaking()` sets a different language for one thread, for example for a report whose
language is preset to the program language.

Stored words (step titles, template lines, result names) can be written in any catalogue
language. `in_language()` recognises them through the catalogues and returns them in the current
language; anything unknown stays as it is. These words are in `stored*.yaml`. So a template
written in German also reads as an English report. The supplied standard template is
English and is stored in the program language when the database is created.

Structure kinds and features come in English from `data/kinds.yaml`. When read from the database
they appear in the current language as long as their name is one of the supplied ones, in whatever
language; it is recognised through the key, so that “Leiter” stays the ladder. A
renamed kind keeps its name.

Supplied test plans (`data/plans/`) and the measurement instructions of the drivers are English. On
loading, `campaign/plan_language.py` translates their texts (title, settings, warnings, steps,
source, connection diagram) into the program language; the German versions are in
`data/languages/de/instructions.yaml`. Keys, functions, sockets and terminal IDs stay
untranslated. A self-written plan stays in the language in which it was written.
A campaign stores its steps in the language at its start; reports in a different
language find the title again through the catalogues.

`tests/test_l10n.py` requires, for every marked text and every word of the supplied plans and
instructions, a German entry with the same placeholders, and reports entries that nothing
uses.

## Instrument abstraction

Three layers: driver, mapping, vocabulary. In detail and with the example of a
sound level meter in [hardware-abstraction.md](hardware-abstraction.md).

`devices/base.py` defines `MeterDriver`: `identify()`, `read_clock()`, `read_measurements()`
and optionally `subscribe_live()`. The interface only reads. It can neither start a measurement
nor change instrument settings, because the inspector does that at the instrument. A new instrument
is a new driver in `devices/registry.py`; the application stays unchanged. Only its mapping knows the codes of the
instrument (`devices/profitest_prime/mapping.py`); functions, results,
quantities, result words and settings are named in the app after their vocabulary
(`easymeasurement/vocabulary/`, `data/vocabulary/*.yaml`).

When a campaign starts with an instrument, the instrument identity, the clock offset and the measurements
already present are recorded. After that only what is new is fetched, with corrected time.

### PROFITEST PRIME

USB CDC at 115200 8N1 or Bluetooth over an RFCOMM socket (channel 1). The inspector only chooses the
instrument; the app does not show ports and addresses. `discovery.py` finds it through the USB ID
(1CD7:0117) and among the paired devices of BlueZ; a paired instrument is also in the
list when it is switched off. Internally the port is called `/dev/ttyACM0` or `bt:<address>`.

Once, the dialog under “Settings” sets up the Bluetooth pairing. For this `pairing.py` drives
`bluetoothctl` with an agent for the PIN. The PIN is not stored.

A campaign starts in every switch position in which the clock can be set. The
instrument memory is not read in doing so, because over Bluetooth that takes 15 s and needs the position Setup.
Instead time separates old and new: new is what lies from `stored_since` on.

Instrument accesses run through `run_busy()` outside the GUI thread. The database connection belongs to
the GUI thread, so the workers only read from the instrument and storing follows afterwards.

**Instrument texts:** measurements keep the TS codes the instrument sends for measured quantities and
settings, as IZYTRON does too (there with the prefix `PROFITEST_`). The words for them are in the
translation file of the instrument (`DATABASEXML:GET:TRANSLATIONFILE`, 12 languages, about one minute over
Bluetooth). When setting up through “Settings → Instruments”, over Bluetooth after pairing or over
USB with “Set up …”, the program checks what is present and transfers what is missing
(`ui/instrument_prepare.py`, tables `device_texts` and `device_text_sets`). The texts apply to the
firmware with which they were read; if a campaign start finds a different firmware, the same
comparison follows with a waiting window. Settings are shown in words, such as “RLO - Polung: Automatische
Umpolung”; without texts the code stays. The IZYTRON import keys settings by code in the same way,
conductor references neutrally as `conductor`. The manufacturer texts belong to the local data, never into the repo.

**Test and instrument log:** “Settings → Instruments → Test …” connects briefly and checks
connection, instrument ID, calibration, clock, rotary switch, subscribing to and unsubscribing from Push/Print and the
instrument texts (`devices/instrument_check.py`, `ui/instrument_test.py`). Nothing is set or measured
in doing so; a deviating clock or an overdue calibration is a notice, not an error. Every run
stays in `instrument_tests`. “Instrument log …” shows per serial number the history from these runs
and the campaigns in which the instrument was used, with firmware, calibration and the deviation of the
clock as found before setting it (`campaign/instrument_history.py`, `ui/instrument_log.py`).
The log needs no connection.

`transport.py` keeps a fixed list of allowed commands: read commands, the three commands of the
push mode and the query of the rotary switch. Everything else is rejected before sending, because write commands replace the
instrument contents and an unknown command could trigger a measurement with real test voltage.

A reader thread owns the connection and separates replies from unsolicited events. Commands
run one at a time; replies are matched through the command echo. Commands without an XML form reply with
a text line without echo.

**Rotary switch:** `read_selector()` returns the position and the possible functions. It is queried only at
fixed points: when a step is set up and at the press of a button, never continuously and never during a
step that is measuring. The instrument writes an event piece by piece, and nothing keeps a reply from
landing in the middle of it.

**Push/Print:** `subscribe_live()` switches the mode on. Every press of Save produces one event; the
measurement goes to the callback first, the acknowledgement after that. A push does not stay in the instrument memory,
so the receiver has the only copy. That is why even an unreadable record is delivered unchanged
as the function `unreadable`. The driver leaves the mode on closing, at
program exit, and after a crash on the next connect. If the connection breaks, it reports this
and reconnects, but only to the same instrument. The callbacks run on a thread of their own.
Only the interface that subscribed can unsubscribe. If that fails, or the
connection comes back by another route, the app asks to switch the instrument off and on again.

- Stored measurements are fetched on request, not continuously: the instrument shows
  a screen of its own meanwhile. It releases them only with the rotary switch at Setup;
  otherwise error 402 comes.
- The instrument codes (`TSnnnn`) in `mapping.py` follow the translation file of the instrument. Unknown
  codes are kept as code and named from the instrument texts when shown.
- The instrument has only one voltage function. If it brings line-to-line voltages, it counts as
  phase sequence measurement `u3`. The phase sequence itself is in `VERIFICATION` and is stored as a neutral word
  (`right`, `left`), so that reports in any language stay possible.
- The instrument writes the ohm sign U+2126, not the Greek omega. `Quantity.parse`
  normalises the unit; `raw` keeps the original.
- `passed` only counts next to a limit. Pure information values such as the mains voltage come
  with `passed="false"` even in passed measurements.

## Import from IZYTRON

`importing/izytron.py` reads a copy of the IZYTRON database read-only and creates one test day as a
closed campaign, with installation tree, measurements and visual inspection. The offset of the instrument clock
on that day is given by the call; it depends on the date. Times from visual inspections are already local time.
Department and contact person come along: the department of the installation (`Abstract_Device.Department`),
otherwise that of the contact person, and the first active contact person of the customer (`Contact`) with
phone, as a substitute mobile number, and e-mail. The cost centre that IZYTRON keeps per test object
belongs to the customer; it is not taken over, because the cost centre of a campaign is the own one.

    python -m easymeasurement.importing.izytron KOPIE.sqlite --offset -120

## Instrument clock

The clock of the instrument has no time zone and no daylight saving time, and loses about 35 s per month.
That is why `CampaignService.start()` sets it to the laptop time before every campaign, without asking.
The aim is that there is no offset. For this the laptop time must be right, that is, run via NTP.

Setting is verified: if a deviation of 3 s or more remains, the campaign does not start.

In the normal case there is therefore no offset, and the user interface shows nothing about the clock: the
status display appears only for an unchecked or deviating clock, the report line “Instrument clock”
only when an offset has actually corrected times. “Instrument → Set clock …” checks and sets
after asking, in any position of the rotary switch. A push does not stay in the instrument memory; if the
connection has run without interruption since the start of the campaign, nothing with the old time is there, and
the clock is set directly. After an abort, a pause or a restart of the program it first fetches
what is stored in the instrument; this fetch needs the position Setup. The offset is kept as a safeguard. `clock_checks` records every check, every measurement
stores its offset (`clock_offset_s`) next to `device_time` and `local_time`. It is needed
for instruments without a settable clock, for a deviation during the campaign and for measurements of an
earlier day, whose offset can be given by hand. If the clock is set during a campaign,
the app asks beforehand and first fetches the measurements from the instrument that still carry the old time.

## Measurement campaign

The main window is ordered by the work, not by kinds of data. In the middle is the
chosen campaign (`ui/campaign_page.py`) with its measured values, on the right, collapsible, location, test plan,
chosen measurement, its readings, its files, photos and reports (`ui/side_panel.py`). The editor of the
measurement hands its table of readings and its attachments to sections of their own
(`ui/campaign_detail.py`), whose headings count what they hold; for an open point, a run or no row they
stay hidden. Sections without content shrink there to a grey line that says what would appear there;
only open sections with content get free height.

The list of all campaigns (`ui/campaign_list.py`) does not lie permanently next to the work. It slides
in as a drawer (`ui/edge_drawer.py`) over the content as soon as the mouse touches the left window edge,
and disappears again when the mouse leaves it; F9 slides it out as well. In the
maximised window it is enough to push the mouse to the screen edge. For this the mouse is
polled at intervals, not tracked, so that no widget has to report its movements. “View →
Pin campaign list” puts it fixed next to the pages; its width is then kept across
a restart. The button with the house before the title leads to the overview.

To the left of the measured values is the structure of the installation like folders in a file manager
(`ui/structure_tree.py`): dragging rows of the table onto an element rebooks them; context menu, F2,
Del and Ins work on the tree. Without a mouse, “Move to …” in the context menu of a row rebooks
(`ui/move_overlay.py`). The number per element is “this inspection / last inspection”. Tree and table
are in a drawn frame (`ui/board.py`): at the top across the full width the line with what
all rows have in common, and the count, below it one toolbar of equal height each,
then the header rows of tree and table on one line. The toolbar of the table holds only
“By hand …” and a filter field; edit, photo, move and delete of a row are in
its context menu and on F2 and Del, so nothing stands permanently greyed out in the picture. Explanatory
sentences are tooltips: at the header “Structure” and at the hint above the frame, whose bold part
stays visible. Between the main blocks of the window lie 8 px of window background; a
stored splitter position does not change that.

Measuring function, measurement and test run are three levels. The measuring function says what is measured
(RISO, RLO). A measurement is a result, a measured value or the answer to a question. A
test run (table `runs`, `campaign/runs.py`) is a named sequence of such steps, for example a
visual inspection by questionnaire: the measurement points to it with `run_id` and names in `step_name`
its step (“Accessibility”). The IZYTRON import creates a test run for every inspection entered at the PC;
measurements from the instrument stay single. In the table a test run is one
row with name, number of steps and defects (`ui/measurement_runs.py`); a click on the time
folds the steps open below it. When sorting they stay below their head, whatever the
column and whatever the direction. Moving the row moves all steps. In the seal,
test run and step name appear only where they exist, so that older seals stay valid.

The user interface speaks of measurements and inspections, not of functions: what is measured are
measured quantities with value, unit and limits, assessed together. The column “Designation” names the
measured quantity (RISO) or, for an inspection, the step (Accessibility). Internally the key stays
`function`, because instrument and report distinguish by it.

A repeat inspection (`campaign/repeat.py`, `campaign/repeat_checks.py`) turns the last
confirmed campaign of the same installation into a list of open points. They lie as steps with the
plan key `repeat` in the campaign and carry element, designation, limits and settings
of the measurement back then, its origin, hint and remark, but no measured value. The list is
filled in any order; there is no guided sequence: every measurement that arrives, by
Push&Print, by hand or by rebooking, takes the open point at the same element with the same
designation; several such points are separated by the conductor (L1-PE, …). If a limit or setting
differs from last time, confirming requires a reason; the program sets nothing at the instrument,
it only checks what arrived. A point can be skipped with a reason. Confirming is possible as soon as
no point is open any more. Open points are grey in the table (`ui/campaign_points.py`), the
structure tree shows with “now / last time” where something is still missing. When chosen, a point shows in the
side panel (`ui/repeat_point.py`) what is to be measured, the hint from last time to take over,
edit or discard, the remark from back then and the photos of the measurement back then; new
measured values then land at its element. Below a measurement that has taken a point, the
values from last time appear only after that, with a notice on a marked change (`ui/repeat_compare.py`).

Besides the remark that appears in the report, every measurement has a hint on how it was carried out. It
comes back at the next repeat as the hint for the point. The report shows it only beneath the
measurement's photos marked as a notice, before the texts of their marks, and in the remark of the
notices table (`reporting/footnotes.py`, `photo_texts`).

In the measurement box, instead of a long path, the booked element is shown with its icon, above it small
and shortened from the left the way to it (`ui/place_line.py`). The pen next to it rebooks the measurement,
the name shows the element in the tree. Only a measurement without an element shows the free location text.

Overlays that change something have “Apply” and “Cancel”; only “Apply” saves. This
also holds for the properties of an element, whose form in the master data, in contrast, stores every finished field
at once. Lists in which every change has its own dialog close with “Back”.

Below the buttons in the header is what remains until confirmation (`ui/campaign_checks.py`):
measurements without location, defects and open points, or “ready to confirm”. “without location” jumps to
these measurements, “defects” from defect to defect; the tooltip names the open points.

The columns of the measured value table are managed by `ui/table_columns.py`: dragging at the header arranges
them, a click sorts. The context menu of the header sorts by the clicked column
and shows and hides columns. Time, photo count and measured value sort by their value instead of by
the text, measured values first by function, then by magnitude. A column whose value is the same in all rows
gives way to the line above the table as long as “Name equal values above the table” is
on; columns hidden by hand stay away in any case. Arrangement, sorting and selection
apply per view and are kept for the next start. Every row begins with a mark for its
verdict (`ui/verdict_marks.py`) that differs in shape and colour, even when the column
“Verdict” is shown above as a common value. For inspection questions the answer stands before the question
(`ui/measurement_cells.py`), such as “no – Is complete circuit documentation available?”.

With a test plan, connection diagram and instructions of the step are above the measured values; without a plan only the
hint on what to do next. Without a plan, “Help → Measurement instructions” (F1) fetches the instructions for the
measuring function set. Connection, instrument clock and state of the campaign are in
the status bar, so always in view.

Without a chosen campaign the middle shows the overview (`ui/dashboard.py`): open and
closed measurements separately as cards with their next step, a search over all of them and
tiles for master data, test plans, templates, archive, users and instrument. The order follows
the data (start, last measurement, closing, last report); the campaign for which
measuring is going on is always in front. The program starts there; “Overview” (Alt+Home) leads back
without interrupting a running measurement.

Title and installation of an open campaign are changed by “Edit campaign …” (`ui/campaign_edit.py`). The
installation may only change if afterwards no measurement and no file is attached to a location outside the new
installation (`misplaced` in `campaign/editing.py`); moving to the parent installation is therefore always possible.
“New campaign” and “Edit campaign” ask for contact person and order in the same way
(`ui/campaign_order.py`): the contact person is visible; department, extension, e-mail,
cost centre and order number fold open below. A new campaign proposes the last
contact of the customer; cost centre and order number belong to one order and start
empty.
A right click in the campaign list offers what is currently possible with the campaign.
A campaign is deleted after asking; its folder with photos, files and reports goes
to the trash. For a sealed one an entry remains in `deleted_campaigns` with its seal
and an HMAC from the same key. The seal check of the next campaign accepts it. The
trigger `campaign_no_delete` lets a sealed campaign go only with this entry, so whoever deletes
bypassing the program still breaks the chain.
The change log stays on deletion; since SQLite reassigns IDs of deleted rows,
an entry belongs only to the measurement whose `device_uid` and campaign it carries.

What does not belong to the single campaign opens a window of its own next to it: master data, templates,
report archive and the search over all measured values. Buttons and menus share the same `QAction`,
so that they never offer something different.

Window sizes, splitters, collapsed sections and hidden bars are kept across a
restart (`ui/view_memory.py`). Splitters are stored while dragging, not on
exit: at that point, for example, the section of the guided step is often not visible at all and would come back without space.

**Viewing and measuring are separate.** A click in the list shows a campaign without touching the
instrument. Only “Resume measuring” or a double click gives it the instrument. The window therefore
remembers two campaigns: the one shown (`campaign_id`) and the one measuring (`live_id`). Whoever views another
campaign during a measurement interrupts nothing. Every reading carries the campaign to which its
session belongs and lands there, whatever is currently shown. Instrument actions are locked
as long as the instrument is measuring for another campaign.

As long as a campaign is measuring, `LiveSession` keeps the instrument in push mode and reconnects when it
disappears. A push goes first into `CampaignService.receive()`, which stores it at once, assigns it to the
active step or leaves it open. The connection is exclusive: for fetching from the instrument
and the clock check the session briefly steps aside (`ui/instrument_control.py`). Before closing
it is disconnected, so that no reading hits a closed record.

## Photos and attachments

A photo is not a measured value but is in its own table `photos`. Its capture time stays
unchanged; `placement` says what decides its assignment:

- `timeline`: it belongs to the nearest measurement. A shift (`photo_shift_s`) moves all
  photos, a gap (`photo_gaps`) everything from its point in time on.
- `pinned`: a person has assigned it to a measurement; the timeline leaves it alone.
- `stack`: it lies on the stack without assignment; the file is kept.

The timeline (`ui/photo_timeline.py`) shows measurements and photos on a time axis as in video editing.
A line connects every photo with its measurement. Dragging a photo sideways shifts all of them, dragging it
upwards onto a measurement assigns only this one firmly. The track under the pointer decides what
happens on release, and the hint line says so beforehand. Photos can also be dragged onto a table row.
The timeline is a tool for assigning: it is below the table as long as it is needed.
“Assign photos” in the header of the campaign (F7) shows it, “Close” in its bar hides it again;
after an import it opens by itself. A scroll bar below the tracks follows zoom and panning.
The stack is in the side panel.

The image files are not in the database but unchanged in the folder of the campaign
(`campaigns/<uuid>/photos/`), named after the beginning of their SHA-256 checksum. The table `photos`
keeps file name, checksum, capture time and assignment; through the checksum the seal also covers the
file. A photo is never converted: the original remains the evidence. Enlarging would add no
detail, so there is no minimum resolution by upscaling; the photo view names the
pixels and warns below 1000 on the long side that the photo looks coarse in the report.

Rotating and cropping do not change the original. A photo has a view
(`campaign/photo_view.py`): a rotation by quarter turns clockwise (`rotation`) and after that
a section of the rotated image (`crop`, as fractions “x y width height”). The large photo view
rotates and crops; marks refer to the view and are converted on a change,
so that they stay on the same spot. Report and thumbnails show the photo through its
view. The seal includes rotation and crop only where they exist.

For report and thumbnails there are proxies (`campaign/photo_proxies.py`): reduced, upright
rotated JPEG copies with at most 1400 pixels on the long side in the folder `proxies/` of the campaign,
named after original and size. A proxy carries the modification time of its original; if it differs,
it is created again, so proxy and original stay in step. When a campaign is opened and after
an import, missing proxies are created in the background on all cores but one; the status line
counts along, and “View draft” waits until all are finished. Before every report the program removes
proxies without an original, those of a different size and remains of aborted writes; a deleted
photo takes its proxy with it. Without marks the proxy goes into the PDF unchanged, with marks
it is painted on and encoded again. Proxies are not part of the seal and can be deleted at any time. The
report is drawn beside the window, which stays usable meanwhile.

From the photos of the chosen measurement in the side panel (`ui/photo_gallery.py`) a photo can be
dragged onto another row of the table. It then belongs only to that measurement; there is no multiple
assignment. The cross in the corner of every thumbnail detaches the photo from the measurement as long as
the campaign is open: it goes to the unassigned photos; file, marks and role
are kept. Deleting is possible only there. Both kinds are in the section “Photos” of the side panel
as tabs “Measurement” and “Unassigned” (`ui/photo_tabs.py`); holding a photo over
a tab while dragging opens it. Dropped on the tab “Measurement”, it belongs to the chosen measurement. As long as photos belong to no measurement, the section and the
tab are orange, the check line in the header reports “n photos not assigned” and leads there with a click,
and “Confirm” points out that they are missing in the report.

The photo view (`ui/photo_preview.py`, `ui/photo_canvas.py`) takes numbered marks: a
rectangle dragged over the photo gives an area with a number, and the text next to it explains it. A click
on a row highlights its area; with “Show all” off the marks stay hidden
until their row is chosen. Next to it is what the photo goes into the report as: Documentation,
Notice or Defect. Marks (table `photo_marks`, in fractions of the upright rotated image)
and role (`photos.role`) are stored only with “Apply”. The report draws the
frames with their numbers into the photo and puts the role and the texts below the image; a defect
is shown there in red. In the seal both appear only where they exist, so that older seals stay valid.

Attachments (`attachments`) are comments, images and PDFs on a measurement or a location. They always belong
to a campaign, so that a record stays complete in itself. Removing detaches them from measurement
and location; deleting ends them together with the file. Photos, gaps, attachments and their files are part of the seal.

Files and notes of the last confirmed inspection of the same installation appear in a new campaign
grey with date at the respective element (`campaign/carry_over.py`, `ui/place_files.py`). What was then attached to
a measurement of the element counts as at the element; what was attached to the campaign itself, as at the
installation. “Take over” copies the entry into the open campaign; the closed one stays unchanged
and sealed. What has been taken over no longer appears as an offer. Storage at elements independent of
campaigns deliberately does not exist: only a parts list with history would give it a purpose.

## Users

A user has title, name, signature and optionally a certificate (`ui/users.py`). The field of the
signature stands for the line in the report (`ui/signature_pad.py`): the whole field is stored in the
format 4:1; the line lies at three quarters of its height and is recorded in the PNG. With “Align”
the signature is pulled onto the line and resized with the mouse wheel; the report puts the
line of the field onto its own, and descenders reach below it. Of the certificate
only path, holder and expiry date are in the database; the password is never stored. It serves
only for checking and signing. A user who already has campaigns is only hidden on removal.

A campaign refers to the user (`user_id`) and additionally records the name as text
(`tester`). On closing, the signature is added as a copy, and its hash is part of the seal; a draft
shows the current signature of the inspector. Later
changes to the user therefore do not touch the record. As long as the campaign is open, the
inspector can be changed, on request also for the measurements so far. This is recorded, but does not mark any
measurement as changed in the report, because it says nothing about the result. A pushed measurement
names the inspector of the campaign; the text of the instrument stays in `raw_data`.

## Inputs

Inputs are overlays, not windows of their own (`ui/overlay.py`). The card lies over the
dimmed window and is used like a dialog with `exec()`. The work behind it stays visible
and goes on; a measured value arrives during this too. Enter confirms, Esc cancels, a click
beside it does nothing. A grey main button explains itself: to its left is what is still missing.
Overlays can be nested, for example “New …” at the inspector in the campaign start.

## Test plans and wizard

A test plan is a sequence of points: `check` (question with yes, no or skip), `measure`
(measurement) and `note` (hint). Plans are stored as YAML in the table `plans` and are edited under
Settings → Test plans (`ui/plan_editor.py`). Changes save themselves. The test run
(`ui/plan_test_run.py`) shows the plan in the wizard with a simulated instrument in a throwaway database.

The instructions per measuring range belong to the instrument and lie with its driver
(`devices/profitest_prime/instructions/`), one file per measuring function: rotary switch,
settings, warnings, connection diagram, procedure and the operation of the device under test (`dut`). A measuring point
takes them over through its function. The free measurement shows the same instructions on request and there follows
the rotary switch and the last measured value. For a function without instructions the app says so; it never shows anything unrelated.

A campaign gets a plan at its start; more are added through “Assign test plan”. Every point
is recorded as a copy in `steps`, so a corrected plan does not change any campaign.
The steps of one assignment lie next to each other and carry its title; so every assignment stays
a plan of its own (`campaign/plan_blocks.py`), even if the same plan is assigned twice.

The campaign always shows structure and measurements. Its plans are in the side panel under
“Test plans” with their progress (`ui/plan_list.py`). “Run” puts the plan in the place of
structure and table (`ui/plan_run.py`); a campaign started with a plan begins with it straight away.
“Pause plan” leaves everything as it is; a step that is measuring then waits for its setup again;
“Continue” goes on at the first open step. “End plan” asks for a reason with which
every step still open counts as skipped. “Remove” names what goes with it and, after
asking, deletes the steps with all measurements and answers booked on them.

The wizard (`ui/guided.py`) shows one point after the other with progress, Back and Next.
The expected answer goes on at once; any other waits for an optional comment.
Skipping needs a reason. Y, N and S answer without the mouse. An answer is stored like a measured value
(`visual_inspection`), so it appears in the table and in the report. Answering again
replaces the old answer. In the report, answers form a table; hints do not appear there.

A measuring point runs like this: click the setup in the connection diagram, confirm the settings, measure, Next.
With a live connection every value is already there; without it, Next fetches the instrument memory. A measured value
is assigned to the active step if the function fits; otherwise it is listed under “Not assigned”.
Without an instrument, values are entered by hand; they land in the step shown.

Two drafts are supplied (`released: false`). “Machine – electrical inspection” measures; its
connection data come from the operating instructions, limits and order are proposals.
“Visual inspection to DIN VDE 0100-600” asks for the items of inspection (Besichtigen) (6.4.2.2 and 6.4.2.3 a–p),
in its own words and checked per item against at least two independent sources; every question names
its clause. Yes means in order, No is a defect, skipping needs a reason, as with
a sequence of the instrument.

An imported sequence, for example a visual inspection from IZYTRON, becomes a draft plan in the own database
through the context menu of the table, “Take over as test plan” (`campaign/runs.py`): every question
an inspection question, every measurement a measuring step of its function.

### Simulator

`devices/simulator.py` is a full driver: it delivers random values, occasionally outside
the limits, and has a random clock offset. With the measuring function a
wrongly set rotary switch can also be reproduced. Its description carries `simulated=True`; by this, not
by the key, the application recognises simulations. Reports from simulations carry a notice
and cannot be signed.

## Template editor

The templates page shows a template as a block list with properties and a live preview for 0, 1
and 4 measurements. Data are inserted from a list, display conditions are chosen. The tab
“Source” shows the same template as YAML; changes there also apply in the layout.

### Letterhead and closing

The block “Letterhead” opens the report: a QR code with the identifier of the inspection (its UUID,
the same as in the footer), next to it title and lines below, below that a frame with
client and contractor. Every line may contain data fields; a line whose data fields are all empty is left out
together with its label, such as “Phone:” without a number. Department, contact person, extension and e-mail
belong to the campaign, not to the customer: the contact person changes with the order. It is set under
“Edit campaign …”; a new campaign takes over that of the last campaign of the same customer.
In the letterhead it appears below the address of the customer. The own cost centre is also a
value of the campaign and appears with the contractor; it is not carried over into the next campaign. The own
company is set once centrally under Settings → Company (table `company`, one row): name,
address, phone, e-mail, website and logo. Templates access it through the data fields `company.*`;
the letterhead sets the logo to the right of the title. A logo block with an image of its own
remains for templates that need a different image. Warning notices such as “DRAFT” are directly
below the letterhead. The signature line can carry the result framed above it, green for
passed, red for failed; its fields may contain data fields, such as the name of the
inspector.

### Page break

Headings stay with what follows. Before a table a new page begins if the header row
and the first rows no longer fit, before a photo row if one row of images no longer fits. If
a table runs over a page, the next page begins with the heading and “(continued)”, then
the header row. Paragraphs leave no single line at the end or beginning of a page. Column widths
follow the content: every column gets at least its longest word, short values together with their
unit stay on one line, and when space is short only columns with long texts give way. Between
number and unit there is a narrow no-break space.

### Logo

The block “Logo” stands outside the text flow and is placed on the page by coordinates in millimetres,
on the first or on every page. It is moved and scaled on a
page thumbnail, through number fields or with quick positions; the aspect ratio is kept.

The image is embedded into the template (`images:` at the end of the YAML, key from the content) and
reduced on import to at most 1000 pixels edge length. So a template stays complete without extra files,
and an archived report keeps the logo that applied then. SVG files are converted on
import into a transparent bitmap.

If a logo is at the top or bottom page margin, the text gives way. This can be switched off;
a logo in the middle of the page does not displace any text.

## Signature

Signing is done as PAdES with an X.509 certificate from a PKCS#12 file. This can also be an
S/MIME certificate, for example exported from Thunderbird or Kleopatra. The file stays where
it is. The program only remembers its path in `settings.ini`; key and password are stored
nowhere. Before signing, a dialog shows name, e-mail, issuer and validity.
Expired certificates and pure encryption certificates are rejected.

An e-mail certificate gives a technically valid signature. Whether a PDF program shows it as
trustworthy depends on whether it trusts the issuer.
