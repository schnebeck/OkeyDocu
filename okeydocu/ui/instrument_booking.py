# OkeyDocu - okeydocu/ui/instrument_booking.py
# The instruments of one campaign: book one in beside the others, book one out.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Offered for booking are the instruments that measure beside another and are known here; a
campaign with a simulated instrument is offered the simulated ones too. An instrument leaves
only while none of the campaign's readings came from it. The campaign's own instrument is
listed and stays: it leaves with the campaign's link to it, never from here."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, \
    QPushButton

from ..campaign.instruments import InstrumentInUse
from ..devices import DeviceError, FoundInstrument, available_drivers, driver_info, \
    find_instruments, is_simulated
from ..l10n import tr
from .overlay import Overlay

SLOT = Qt.ItemDataRole.UserRole


def booked_label(booked) -> str:
    info = driver_info(booked.driver)
    name = tr(info.label) if info else booked.driver
    who = booked.identity
    return f"{name}: {who.manufacturer} {who.model} ({who.serial_no})" if who else name


class InstrumentBookingOverlay(Overlay):
    def __init__(self, app, campaign_id: int, parent=None):
        super().__init__(tr("Instruments of the campaign"), parent, width=640)
        self.app, self.campaign_id = app, campaign_id
        self.changed = False
        self.booked = QListWidget()
        self.booked.setMinimumHeight(110)
        self.booked.currentRowChanged.connect(lambda _: self._update())
        self.release_button = QPushButton(tr("Book out"))
        self.release_button.clicked.connect(self.release)
        self.offered = QComboBox()
        self.book_button = QPushButton(tr("Book in"))
        self.book_button.clicked.connect(self.book)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.ok_button.setText(tr("Back"))
        self.cancel_button.hide()
        out_row, in_row = QHBoxLayout(), QHBoxLayout()
        out_row.addStretch()
        out_row.addWidget(self.release_button)
        in_row.addWidget(self.offered, 1)
        in_row.addWidget(self.book_button)
        self.body.addWidget(self.booked)
        self.body.addLayout(out_row)
        self.body.addLayout(in_row)
        self.body.addWidget(self.status)
        self.refresh()

    def _offers(self) -> list[FoundInstrument]:
        offers = [found for found in find_instruments(companions=True)
                  if driver_info(found.key).companion]
        if is_simulated(self.app.service.campaign(self.campaign_id)["driver"]):
            offers += [FoundInstrument(info.key, tr(info.label)) for info in available_drivers()
                       if info.simulated and info.companion]
        taken = {booked.identity.serial_no for booked in self.instruments() if booked.identity}
        return [found for found in offers if found.port not in taken or not found.port]

    def instruments(self):
        return self.app.service.instruments(self.campaign_id)

    def refresh(self) -> None:
        self.booked.clear()
        for booked in self.instruments():
            item = QListWidgetItem(booked_label(booked))
            item.setData(SLOT, booked.slot)
            self.booked.addItem(item)
        self.offered.clear()
        for found in self._offers():
            self.offered.addItem(found.label, found)
        self._update()

    def _update(self) -> None:
        item = self.booked.currentItem()
        slot = item.data(SLOT) if item is not None else None
        self.release_button.setEnabled(bool(slot))
        if slot and self.app.service.has_readings(self.campaign_id, slot):
            self.release_button.setEnabled(False)
            self.release_button.setToolTip(tr("It has measured in this campaign."))
        else:
            self.release_button.setToolTip("")
        self.book_button.setEnabled(self.offered.count() > 0)

    def book(self) -> None:
        found = self.offered.currentData()
        if found is None:
            return
        info = driver_info(found.key)
        try:
            identity = info.identity_of(found.port) if info.identity_of else None
        except DeviceError as error:
            self.status.setText(tr(str(error)))
            return
        self.app.service.book(self.campaign_id, found.key, identity, beside=True)
        self.changed = True
        self.status.setText(tr("Booked in: {name}", name=found.label))
        self.refresh()

    def release(self) -> None:
        item = self.booked.currentItem()
        if item is None or not item.data(SLOT):
            return
        try:
            self.app.service.release(self.campaign_id, item.data(SLOT))
        except InstrumentInUse as error:
            self.status.setText(str(error))
            return
        self.changed = True
        self.status.setText(tr("Booked out: {name}", name=item.text()))
        self.refresh()
