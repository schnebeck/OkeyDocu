# OkeyDocu - okeydocu/ui/list_station.py
# The setting lists of the instrument at the station that sets it up.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""At the station that sets the instrument up, each setting whose list the driver knows
carries a link. It puts the list on the drawn display, as the softkey beside the setting does
on the instrument, steps through the settings of that softkey and returns to the view. While
a list is shown the softkeys that work it are pointed at."""

from __future__ import annotations

from html import escape

from ..devices.screen import LIST_KEYS, SettingList
from ..l10n import tr

LINK = "list:"


class ListStation:
    """Mixed into the measuring window, which holds `setting_list`, the driver's way to the
    list of a view's softkey row, and `listed`: the setting of the station whose list is on
    the display and the entry selected in it, or None."""

    def _listing(self, number: int) -> SettingList | None:
        """The list of the station's setting `number`, where the driver knows it."""
        action, view = self._to_set()[number][0], self._view()
        if self.setting_list is None or action.key is None or view is None:
            return None
        return self.setting_list(view, action.key)

    def _list_links(self) -> list[str]:
        """For each setting of the station what its link offers next: to show its list, to
        step on in it, or to return to the view; empty where no list is known."""
        links = []
        for number in range(len(self._to_set())):
            listing = self._listing(number)
            if listing is None:
                links.append("")
                continue
            entry = self.listed[1] if self.listed and self.listed[0] == number else None
            text = tr("Show its list") if entry is None else \
                tr("Back to the view") if entry == len(listing.settings) - 1 else \
                tr("Next in its list")
            links.append(f' <a href="{LINK}{number}">{escape(text)}</a>')
        return links

    def _follow_list(self, href: str) -> None:
        if not href.startswith(LINK):
            return
        number = int(href.removeprefix(LINK))
        listing = self._listing(number)
        entry = self.listed[1] + 1 if self.listed and self.listed[0] == number else 0
        self.listed = (number, entry) if listing and entry < len(listing.settings) else None
        self._show_configure()

    def _list_on_display(self) -> bool:
        """Puts the list being looked at on the display; False where none is."""
        listing = self._listing(self.listed[0]) if self.listed else None
        if listing is None:
            return False
        self.bench.panel.show_screen(listing.at(self.listed[1]), self.place.stated)
        self.bench.panel.point_at(*self.softkeys[:len(LIST_KEYS)])
        return True
