# OkeyDocu - okeydocu/ui/instrument_start.py
# The first contact with the instrument of a campaign that is already open.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A campaign is opened before its instrument is asked anything, so it stays whatever the
instrument does. The first contact reads identity and clock into it; while the instrument does
not answer, the operator tries again or leaves it for later, when the campaign is entered."""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import QMessageBox

from .. import APP_NAME
from ..campaign.service import read_instrument
from ..devices import Cancelled, DeviceError
from ..l10n import tr
from .common import AppContext, run_busy
from .instrument_prepare import prepare_if_needed


def ask_again(parent, error: str) -> bool:
    """True for another try, False to connect later."""
    box = QMessageBox(QMessageBox.Icon.Warning, APP_NAME, error, parent=parent)
    box.setInformativeText(tr("The campaign is open and stays so. Switch the instrument on and"
                              " try again, or connect it later by resuming the campaign."))
    again = box.addButton(tr("Try again"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(tr("Connect later"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(again)
    box.exec()
    return box.clickedButton() is again


def _first_contact(driver):
    with driver:
        return read_instrument(driver)


def reach_instrument(app: AppContext, parent, campaign_id: int) -> bool:
    """True once the instrument has answered and the campaign holds what it told."""
    key = app.service.campaign(campaign_id)["driver"]
    port = app.devices.ports.get(campaign_id, "")
    while True:
        driver = app.devices.new_driver(key, port)
        try:
            text = tr("Connecting to the instrument and setting the clock …")
            start = run_busy(parent, text, partial(_first_contact, driver), driver.abort)
        except Cancelled:
            return False
        except DeviceError as err:
            if ask_again(parent, str(err)):
                continue
            return False
        prepare_if_needed(app, key, port, start.identity, driver.capabilities, parent)
        app.service.take_start(campaign_id, start)
        app.devices.attach(campaign_id, driver, port)
        return True
