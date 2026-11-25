# GUI design rules

Short rules for every window of the application. They say what holds; how the workspace is
built from them is described in [architecture.md](architecture.md).

## Aim

The surface is calm and leads the eye: function blocks are recognisable at a glance, and a
change of state changes what a block says, not where things stand.

## Blocks

- What belongs together stands in one block. A block has a closed frame all round
  (`Framed` in `ui/framed.py`, `Board` in `ui/board.py`).
- No block touches the border of the window (`EDGE`). Blocks of their own keep room between
  them (`GUTTER`), everywhere the same: the columns of a window, the photo timeline below the
  board.
- Blocks about the same subject that stand on each other are the rows of one table: one frame
  around all, a line between the rows, padding inside each row and no room between them. The
  middle of the workspace is such a table: the head of the campaign, what to do now, the head
  of the board, its panes. The sections beside it are another. Narrow strips of background
  between frames are avoided.
- Rows that come and go, such as the sections beside the workspace, close the frame between
  them: the first on show begins it, each closes it below for the next.
- Structure is drawn with lines, not with colour. Colour marks a state: the chips of a status,
  a field with a pending entry, the stations of a guide.

## Stable places

- A row that changes with the state is always there and always as high (`row_height()` in
  `ui/board.py`). With nothing to do it says why, for example that measuring is paused. What
  stands below never jumps.
- Rows that take each other's place, such as measuring without a plan and running a plan, have
  the same height and stand in the same place.
- A text that may run out of room is one line and ends in an ellipsis (`ui/elided_label.py`);
  the whole text waits under the mouse. A row never grows because the window got narrower.
- The texts of a column begin on one line, cut or not, in tables and in lists
  (`ui/steady_text.py`); a column sized to its texts shows them whole.
- The side panel is as wide as what it shows needs and never falls back in width
  (`ui/side_panel.py`), so nothing in it is cut and it does not twitch with the choice. What
  it shows gives way instead of widening it: a name that leads somewhere is a cut link
  (`ElidedLink`), and a row of buttons that would not fit is two rows or arrows.
- A button that changes its text is as wide as its longest text (`ui/button_width.py`).
- Details of the same kind stand on a line each, their names dimmed in one column.

## Lines

- No line ends in nothing. Every line runs from one line to another: a rule from the frame to
  the frame or to another rule.
- All lines have one colour, taken from the text colour (`rule_colour`), so they show on light
  and dark themes alike.
- Lines are laid on the pixels of the screen with `ui/pixel_lines.py`, never drawn in the
  widget's own units: in a window scaled by a fraction such lines vanish or double.

## Edges and spacing

- One unit (`UNIT`, 4 pixels) lies between a frame and what stands in it, two units between
  controls in a row. Bare text stands `TEXT` further in, where the faces of buttons begin.
- What the rows of a table hold begins and ends on the same two lines down the window.
  Controls in different rows share their edges where they can: a width follows the controls
  above it rather than its own content.
- Controls in a bar have one height.

## Words

The program works on a few things. Every text of the surface names the thing it is about, in
the one word the thing has, and the one verb for what happens to it. The words are given as
the German surface shows them, with the English of the code.

| Thing | German | States | Verbs |
|---|---|---|---|
| Campaign: one inspection of an installation, from the first measurement to the report | Kampagne | offen, beendet | beenden |
| Measuring: the instrument sharing its readings with a campaign | Messung (am Gerät) | läuft, unterbrochen | unterbrechen, fortsetzen |
| Measurement: one result in the table | Messung | bestanden, nicht bestanden, nicht bewertet | |
| Defect: a measurement that failed, in the workspace as in the report | Mangel | | |
| Test plan: what is to be checked, step by step | Messplan | Entwurf, freigegeben; run: läuft, unterbrochen, beendet | unterbrechen, beenden |
| Step of a test plan | Messschritt | offen, erledigt, ausgelassen | auslassen |
| Measuring point: what a campaign that repeats an inspection or follows a template still has to measure | Messpunkt | offen, gemessen, ausgelassen | auslassen |
| Report: the document made from a campaign | Protokoll | Vorschau, abgelegt | ablegen |

- To pause means it goes on later (`unterbrechen`); to end means it is over (`beenden`). Ending
  a campaign is final: the question before it says that the record is sealed and nothing can
  be changed afterwards.
- A button names what it does and to what: “Kampagne beenden …”, not “Bestätigen …”.
- A state says whose state it is: “Kampagne offen”, “Messplan: 3 Messschritte offen”,
  “2 Mängel an der Anlage”.
- What stands in the way of a step is said at the control for that step: the button that
  ends the campaign waits and tells why.
- A count that is a link shows all it counts at once, not one after the other.
- A word has one meaning. `Entwurf` belongs to the test plan not yet released; the report
  before the end of its campaign is a `Vorschau`. `Bestätigen` is kept for what is really
  confirmed, such as the setup in a guide.
- A number stands once in a window.

## Checking

- A changed view is looked at as a picture before it counts as done: in the Breeze style, at
  100 % and at 125 % on a real window system, in every state the view has and at a narrow and
  a wide window.
- The rules of the workspace are held by `tests/test_workspace_blocks.py`, those of the lines
  by `tests/test_pixel_lines.py`.
