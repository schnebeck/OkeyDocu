# OkeyDocu - okeydocu/ui/template_names.py
# What a report template is called and which one is the default, in the template editor.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QLineEdit

from ..l10n import tr
from .common import show_error


class TemplateNames:
    """Campaigns know their template by name, so renaming goes through the database, which
    carries the name along; the text being edited stays as it is."""

    def _show_default(self) -> None:
        """The entry is ticked on the default template; on any other it makes that one the
        default. There is always one, so the tick is not taken away by hand."""
        default = self.app.db.default_template()
        is_default = default is not None and default["name"] == self.choice.currentText()
        self.default_action.setChecked(is_default)
        self.default_action.setEnabled(not is_default and self.choice.count() > 0)

    def _make_default(self) -> None:
        self.app.db.set_default_template(self.choice.currentText())
        self._show_default()

    def _rename(self) -> None:
        old = self.choice.currentText()
        name, accepted = QInputDialog.getText(
            self, tr("Rename template"), tr("Name:"), QLineEdit.EchoMode.Normal, old)
        if accepted:
            self.rename(name.strip())

    def rename(self, name: str) -> None:
        old = self.choice.currentText()
        if not name or name == old:
            return
        try:
            self.app.db.rename_template(old, name)
        except ValueError as err:
            show_error(self, str(err))
            return
        self.choice.setItemText(self.choice.currentIndex(), name)
