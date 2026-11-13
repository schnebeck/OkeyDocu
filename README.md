# OkeyDocu

*Field testing and documentation on the go*

Measurement records and test reports for the Linux Plasma desktop.

**Producer:** Thorsten Schnebeck (author, rights holder and responsible person)

Everything revolves around one chain:

    Customer → Installation → Campaign → Measurement → Value → Report

- **Guided measurement:** an animated guide in its own window leads through the first
  measurement of a kind, step by step: test point, rotary switch, measuring leads. The structure
  grows while measuring; elements are created on the way. A simulator delivers random values
  when no instrument is connected.
- **Master data:** customers and their installations, machines and devices as a tree
- **Values:** a number with its unit or a text, plus photos per measurement with numbered
  marks, each classed as a note or a defect.
- **Search and filter:** full text, customer, installation with its sub-installations,
  campaign, quantity, rating, period, value range with unit (`max 1MΩ`), only with photo
- **Reports:** from templates that can show 0, 1 or n measurements per record. Templates are
  made in a graphical editor with live preview; a logo can be imported, scaled and placed
  freely.
- **Archive:** closed campaigns are locked. Archived PDFs carry a checksum and keep the
  template they were made with.
- **Signature:** PAdES with an X.509 certificate from a PKCS#12 file or from an NSS database
  (such as the one of Firefox or Thunderbird), S/MIME certificates included. Where pinentry is
  installed, it asks for the key password.
- **Instruments:** exchangeable behind an abstraction layer. Values can also be entered by hand
  without an instrument.

## Running

    tools/setup-venv.sh
    .venv/bin/python -m okeydocu

`tools/install-desktop-entry.sh` adds the program to the start menu: the script registers the
launch from this checkout and the program icon for the logged-in user (`--remove` takes both
out again).

The `.venv` is isolated and uses the pinned versions from `requirements.txt`. Only PySide6 comes
from the distribution (package `python3-pyside6`), because it has to match the system Qt for the
Plasma style to load. Data is kept in `~/.local/share/OkeyDocu`; `OKEYDOCU_DATA` selects another
folder.

## Tests

    .venv/bin/python -m pytest

## Photos

Photos are assigned to a measurement by the time they were taken. The time comes from the EXIF
data, otherwise from the file name. Messengers strip EXIF data: better transfer photos over USB
or KDE Connect. A photo without a clear assignment is kept as an entry of its own and can be
searched for.

More in [docs/architecture.md](docs/architecture.md).

## License

GPL-3.0-or-later, see [LICENSES](LICENSES/GPL-3.0-or-later.txt).
