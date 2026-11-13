# OkeyDocu - okeydocu/devices/base.py
# The one interface the application sees. Instruments stay behind it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, Flag, auto
from typing import Callable

from ..l10n import tr
from ..model import DeviceIdentity, MeterMeasurement


class DeviceError(Exception):
    """The instrument could not be reached or answered with an error."""


class Cancelled(DeviceError):
    """The operator stopped the work before it was done; nothing is to be reported."""


class DeviceBlocked(DeviceError):
    """The instrument is there but will not hand out its stored data right now."""


class Capability(Flag):
    NONE = 0
    READ_STORED = auto()  # stored measurements can be fetched on request
    CLOCK = auto()  # the instrument clock can be read
    SET_CLOCK = auto()  # the instrument clock can be set to the laptop's time
    LIVE_RESULTS = auto()  # the instrument reports results as they happen
    SELECTOR = auto()  # the position of the function selector can be read
    SIMULATED_TRIGGER = auto()  # test drivers only: the app may create a reading
    TEXTS = auto()  # the instrument hands out its words for the codes it sends


@dataclass(frozen=True)
class DeviceTexts:
    """Code to text for each language, as the instrument names them (`de-DE`)."""

    version: str
    texts: dict[str, dict[str, str]]


@dataclass(frozen=True)
class FoundInstrument:
    """Something the operator can choose. `port` is the driver's business, never shown."""

    key: str
    label: str
    port: str = ""


class LinkState(Enum):
    CONNECTED = "connected"
    LOST = "lost"
    ERROR = "error"


@dataclass(frozen=True)
class LiveReading:
    """A measurement as it arrived: `received_at` is the laptop's own clock."""

    measurement: MeterMeasurement
    received_at: datetime


@dataclass(frozen=True)
class SelectorPosition:
    """Where the function selector stands, as far as the instrument's meaning is known.

    `label` is what the switch says, empty if it stands on no measuring function.
    `functions` is what this position can produce, empty if it does not tell.
    `value` is what the instrument reported, for a drawing of its dial; None if unknown.
    """

    label: str = ""
    functions: frozenset[str] = frozenset()
    value: int | None = None

    def rules_out(self, function: str) -> bool:
        return bool(self.functions) and function not in self.functions


class MeterDriver(ABC):
    """An instrument, seen from the application.

    The interface is deliberately read-oriented. The operator sets up and
    starts every measurement on the instrument itself; nothing here can start
    a measurement. Its clock is the one setting that can be changed.
    """

    capabilities: Capability = Capability.NONE
    stop_warning = ""  # what the operator has to do after a connection that ended badly

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def identify(self) -> DeviceIdentity: ...

    @abstractmethod
    def read_clock(self) -> datetime:
        """Return the instrument's current time as a naive local datetime."""

    @abstractmethod
    def read_measurements(self) -> list[MeterMeasurement]:
        """Return every measurement stored on the instrument."""

    def sync_clock(self) -> None:
        """Set the instrument's clock to the laptop's local time."""
        raise DeviceError(tr("The clock of this instrument cannot be set."))

    def read_selector(self) -> SelectorPosition:
        """Where the function selector stands. Raises DeviceError if that cannot be told."""
        raise DeviceError(tr("This instrument does not report its rotary switch."))

    def subscribe_live(
        self, on_reading: Callable[[LiveReading], None],
        on_state: Callable[[LinkState, str], None] | None = None,
    ) -> None:
        raise DeviceError(tr("This instrument delivers no live results."))

    def unsubscribe_live(self) -> None:
        pass

    def abort(self) -> None:
        """Called from another thread: a command waiting for its answer ends at once with a
        DeviceError. Only reading is ever cut short; the caller still closes the driver."""

    def read_texts(self) -> DeviceTexts:
        """The instrument's words for its codes. Slow: read when it is set up, not to measure."""
        raise DeviceError(tr("This instrument delivers no texts."))

    def __enter__(self) -> "MeterDriver":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
