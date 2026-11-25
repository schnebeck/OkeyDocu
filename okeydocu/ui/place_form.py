# OkeyDocu - okeydocu/ui/place_form.py
# Station "Installation", right side: which element, and what the guide needs it to state.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The element is chosen in the structure tree, which can be worked on as anywhere else: new
elements of every kind, renamed, moved, grouped and deleted. Where the guide is taken at a
kind of element of its own, such as an RCD, and none stands at or above the chosen one, a new
one is entered that will hang below it. A missing statement is marked, not demanded: going on
without it keeps the measurement possible and the drawing in its usual layout. What is entered
is stored when the tester goes on, as if entered in the element's own form."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..campaign.measuring_place import MeasuringPlace
from ..devices.guide import Guide
from ..l10n import N_, tr, value_text
from .choice_box import feature_field, field_text
from .element_form import ElementOverlay
from .pending_marks import PendingMarks
from .structure_panel import StructurePanel

MISSING_STYLE = "background:#fde2c4"
HINT = "#b35c00"
TREE_HINT = N_("Choose the element that is measured. A right click or Ins makes new elements"
               " of every kind below the chosen one; dragging moves them.")
ENTER = (Qt.Key.Key_Return, Qt.Key.Key_Enter)


class PlaceForm(QWidget):
    chosen = Signal(object)  # an element picked in the tree; None: the installation itself
    changed = Signal()  # the structure was worked on
    edited = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.place = MeasuringPlace(None)
        self.fields: dict[str, QWidget] = {}
        self.quiet = False  # the tree is being set, not worked on
        self.panel = StructurePanel(app)
        self.panel.set_hint(tr(TREE_HINT))
        self.panel.setMinimumHeight(180)
        self.panel.search.installEventFilter(self)
        self.panel.tree.chosen.connect(self._picked)
        self.panel.tree.changed.connect(self.changed)
        self.panel.actions.properties_requested.connect(self._properties)
        self.name = QLineEdit()
        self.identifier = QLineEdit()
        for line in (self.name, self.identifier):
            line.textEdited.connect(lambda _: self.edited.emit())
        self.new_title = QLabel()
        self.new_title.setWordWrap(True)
        self.new_form = QFormLayout()
        self.new_form.addRow(tr("Designation"), self.name)
        self.new_form.addRow(tr("Identifier"), self.identifier)
        self.form = QFormLayout()
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.data_title = QLabel()
        self.pending_marks = PendingMarks(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"<b>{tr('Where do we measure?')}</b>"))
        layout.addWidget(self.panel, 1)
        layout.addSpacing(8)
        layout.addWidget(self.new_title)
        layout.addLayout(self.new_form)
        layout.addSpacing(8)
        layout.addWidget(self.data_title)
        layout.addLayout(self.form)
        layout.addWidget(self.hint)

    def eventFilter(self, watched, event) -> bool:
        """Enter in the search field stays there and does not press the window's button."""
        return event.type() == QEvent.Type.KeyPress and event.key() in ENTER

    def show_root(self, root_id: int, campaign_id: int) -> None:
        self.quiet = True
        self.panel.tree.show_root(root_id, campaign_id)
        self.quiet = False

    def select(self, asset_id: int | None) -> None:
        """Rebuilt from the database first, so an element just made is there to be chosen.
        None marks no element at all."""
        self.quiet = True
        self.panel.tree.reload()
        if asset_id is None:
            self.panel.tree.setCurrentItem(None)
        else:
            self.panel.tree.select(asset_id)
        self.quiet = False

    def _picked(self, asset_id) -> None:
        if not self.quiet:
            self.chosen.emit(asset_id)

    def _properties(self, asset_id: int) -> None:
        if ElementOverlay(self.app, asset_id, self.window()).exec():
            self.panel.tree.reload()
            self.changed.emit()

    def show_place(self, guide: Guide, place: MeasuringPlace,
                   typed: dict[str, str] | None = None) -> None:
        """`typed` is what the fields hold beyond what the element states, not yet stored."""
        self.place = place
        self.show_parent(place)
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        if not place.kind:
            self.data_title.setText("")
            self.hint.setText(f"<span style='color:{HINT}'>"
                              f"{tr('Choose the element this test is for.')}</span>")
            return
        if place.is_new:
            self.name.setPlaceholderText(tr(self.app.db.kind(place.kind).label))
        self._feature_rows(guide, place.entered(typed or {}))

    def show_parent(self, place: MeasuringPlace) -> None:
        """What a new element is and below which one it will hang."""
        self.new_title.setVisible(place.is_new)
        for row in range(self.new_form.rowCount()):
            self.new_form.setRowVisible(row, place.is_new)
        if place.is_new:
            text = tr("New {kind} below “{parent}”", kind=tr(self.app.db.kind(place.kind).label),
                      parent=place.path[-1] if place.path else "")
            self.new_title.setText(f"<b>{text}</b>")

    def _feature_rows(self, guide: Guide, place: MeasuringPlace) -> None:
        kind = self.app.db.kind(place.kind)
        lists = self.app.db.choice_lists()
        features = {feature.key: feature for feature in kind.features}
        self.data_title.setText(f"<b>{tr('Details from the rating plate')}</b>")
        for key in guide.element_features:
            if key not in features:
                continue
            field = feature_field(features[key], str(place.features.get(key) or ""), lists)
            field.setStyleSheet(MISSING_STYLE if key in place.missing([key]) else "")
            above = place.inherited.get(key, "")
            if above and not place.features.get(key):
                edit = field.lineEdit() if isinstance(field, QComboBox) else field
                edit.setPlaceholderText(tr("{value}, as stated above", value=value_text(above)))
            edits = field.editTextChanged if isinstance(field, QComboBox) else field.textEdited
            edits.connect(lambda text, field=field, above=above: self._typed(field, text, above))
            self.fields[key] = field
            unit = features[key].unit
            self.form.addRow(tr(features[key].label) + (f" ({unit})" if unit else ""), field)
        hint = tr("Missing details are stored at the element. Without them the drawing shows"
                  " the usual layout.")
        missing = place.missing(self.fields)
        self.hint.setText(f"<span style='color:{HINT}'>{hint}</span>" if missing else "")
        self.pending_marks.watch()

    def _typed(self, field, text: str, above: str = "") -> None:
        field.setStyleSheet("" if text.strip() or above else MISSING_STYLE)
        self.edited.emit()

    def entered(self) -> dict[str, str]:
        """What differs from what the element stated."""
        values = {key: self._value(field) for key, field in self.fields.items()}
        return {key: value for key, value in values.items()
                if value != str(self.place.features.get(key) or "").strip()}

    def title(self) -> str:
        """Name and identifier of an element still to be made, as they read so far."""
        name = self.name.text().strip() or self.name.placeholderText()
        return " ".join(part for part in (self.identifier.text().strip(), name) if part)

    @staticmethod
    def _value(field) -> str:
        return field_text(field).strip()

    def store(self) -> bool:
        """Stores what was entered at an existing element; whether anything changed."""
        changed = self.entered()
        if changed and self.place.asset_id is not None:
            features = dict(self.place.features)
            features.update(changed)
            self.app.db.set_asset_features(self.place.asset_id, features)
        return bool(changed)
