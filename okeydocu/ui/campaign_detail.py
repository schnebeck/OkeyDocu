# OkeyDocu - okeydocu/ui/campaign_detail.py
# The chosen row of the table at the side: the measurement, its readings and its files.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..l10n import tr


class CampaignDetail:
    """Each part of the measurement has a section of its own, so each folds on its own."""

    def _show_detail_room(self, chosen: bool, photos: int, run: str) -> None:
        """Sections without anything to show shrink to a line that says why."""
        if run:
            self.detail_section.set_empty(tr("“{run}” has several steps. A click on the time"
                                             " unfolds them, then each can be edited on its own.",
                                             run=run))
        else:
            self.detail_section.set_empty(None if chosen else tr("Choose a row of the table."))
        self._show_parts()
        if photos:
            self.photo_tabs.show_note(None)
        elif chosen:
            self.photo_tabs.show_note(tr("No photos for this measurement. Drag photos onto the"
                                         " row or attach them with a right-click."))
        else:
            self.photo_tabs.show_note(tr("Shows the photos of the chosen measurement."))
        self._quiet_photos()

    def _show_parts(self) -> None:
        """Readings and files belong to a single measurement; for an open point, a run or no
        row at all their sections stay away. Their headings count what they hold."""
        editor = self.values.editor
        measured = editor.row is not None and self.values.current_point() is None
        for section in (self.readings_section, self.files_section):
            section.setVisible(measured)
        if not measured:
            return
        readings = len(editor.rows.rows)
        self.readings_section.set_count(readings)
        self.readings_section.set_empty(None if readings else tr("No readings."))
        files = editor.attachments.list.count()
        self.files_section.set_count(files)
        # An open campaign offers to attach files, so the section stays open for that.
        self.files_section.set_empty(None if files or editor.editable else tr("No files."))
