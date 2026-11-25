# OkeyDocu - okeydocu/ui/list_station.py
# The setting lists of the instrument at the station that sets it up, worked by its softkeys.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""At the station that sets the instrument up, the softkeys of the drawn panel work as on the
instrument wherever the driver knows the list of a setting. A click on the softkey beside a
setting opens its list on the drawn display; there the softkeys move the cursor up and down,
pass to the choices, confirm the one under the cursor and take the list over, which closes
it. What was taken over stands in the list the next time, and a setting that describes the
test point shows on the view from then on. A link beside each such setting opens the list as
well and steps through its settings."""

from __future__ import annotations

from dataclasses import replace
from html import escape

from PySide6.QtCore import QEvent, Qt

from ..devices.guide import CONFIGURE
from ..devices.screen import LIST_KEYS, SettingList
from ..l10n import N_, tr
from .list_art import reading, spot_of

LINK = "list:"
CLICKABLE = N_("The softkeys in the picture can be pressed: a click works them as on the"
               " instrument.")


class ListStation:
    """Mixed into the measuring window, which holds `setting_list`, the driver's way to the
    list of a view's softkey row; `listed`, the station's setting whose list is open with
    the list as it stands, or None; `taken`, what was taken over in a list, by guide and
    setting; `set_values`, what that means for the features a view shows; and `key_press`."""

    def _listing(self, number: int) -> SettingList | None:
        """The list of the station's setting `number` as it opens, where the driver knows
        it, with what was taken over in it before."""
        action, view = self._to_set()[number][0], self._view()
        if self.setting_list is None or action.key is None or view is None:
            return None
        listing = self.setting_list(view, action.key)
        taken = self.taken.get((self.guide.function, number), ())
        return replace(listing, taken=taken) if listing is not None else None

    def display_stated(self, key: str) -> str:
        """What the display shows of the test point: as set in a list, else as stated."""
        return self.set_values.get(key) or self.place.stated(key)

    def _list_links(self) -> list[str]:
        """For each setting of the station what its link offers next: to show its list, to
        step on in it, or to return to the view; empty where no list is known."""
        links = []
        for number in range(len(self._to_set())):
            listing = self._listing(number)
            if listing is None:
                links.append("")
                continue
            shown = self.listed[1] if self.listed and self.listed[0] == number else None
            text = tr("Show its list") if shown is None else \
                tr("Back to the view") if shown.selected == len(shown.settings) - 1 else \
                tr("Next in its list")
            links.append(f' <a href="{LINK}{number}">{escape(text)}</a>')
        return links

    def _list_hint(self) -> str:
        known = any(self._listing(number) for number in range(len(self._to_set())))
        return f"<p>{escape(tr(CLICKABLE))}</p>" if known else ""

    def _follow_list(self, href: str) -> None:
        if not href.startswith(LINK):
            return
        number = int(href.removeprefix(LINK))
        if self.listed and self.listed[0] == number:
            shown = self.listed[1]
            last = shown.selected == len(shown.settings) - 1
            self.listed = None if last else (number, shown.at(shown.selected + 1))
        else:
            listing = self._listing(number)
            self.listed = (number, listing) if listing is not None else None
        self._show_configure()

    def _list_on_display(self) -> bool:
        """Puts the open list on the display; False where none is open."""
        if self.listed is None:
            return False
        self.bench.panel.show_screen(self.listed[1], self.place.stated)
        self.bench.panel.point_at(*self.softkeys[:len(LIST_KEYS)])
        return True

    # The softkeys of the drawing ----------------------------------------------------------

    def eventFilter(self, watched, event) -> bool:
        pressed = event.type() == QEvent.Type.MouseButtonPress and self.kind == CONFIGURE
        if pressed and watched is self.bench.panel and event.button() == Qt.MouseButton.LeftButton:
            for index, key in enumerate(self.softkeys):
                at = self.bench.panel.part_rect(key)
                if at.contains(event.position()):
                    self.key_press.press(at)
                    self.press_softkey(index)
                    return True
        return super().eventFilter(watched, event)

    def press_softkey(self, index: int) -> None:
        """The softkey `index`, counted from the top, as the instrument takes it: on the view
        it opens the list of the setting beside it, in a list it works the list."""
        if self.listed is None:
            beside = [number for number, (_, parts) in enumerate(self._to_set())
                      if self.softkeys[index] in parts and self._listing(number) is not None]
            self.listed = (beside[0], self._listing(beside[0])) if beside else None
        else:
            number, listing = self.listed
            keys = listing.keys()
            key = keys[index] if index < len(keys) else ""
            if key in ("up", "down"):
                listing = listing.moved(-1 if key == "up" else 1)
            elif key == "right":
                listing = listing.across(self._start(listing))
            elif key == "enter":
                listing = listing.confirmed()
            self.listed = (number, listing)
            if key == "take":
                self._take_over(number, listing.confirmed())
        self._show_configure()

    def _start(self, listing: SettingList) -> tuple[int, int]:
        """Where the cursor lands among the choices: on the value in force."""
        setting = listing.settings[listing.selected]
        in_force = reading(listing, listing.selected, self.place.stated)
        return spot_of(setting, in_force) or (0, 0)

    def _take_over(self, number: int, listing: SettingList) -> None:
        """Closes the list and keeps what was confirmed in it."""
        self.taken[(self.guide.function, number)] = listing.taken
        for index, wording in listing.taken:
            feature = listing.settings[index].feature
            if feature:
                self.set_values[feature] = wording.rpartition(":")[2].strip()
        self.listed = None
