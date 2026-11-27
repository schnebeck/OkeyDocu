# OkeyDocu - okeydocu/devices/climate/bluez.py
# Bluetooth Low Energy through BlueZ on the system bus: listen to advertisements, talk GATT.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every call here blocks and has a deadline; run it off the user interface thread. BlueZ
knows a device only while it hears it, so a connection is made right after listening. No
pairing is needed: the sensors this serves take commands from any client in reach."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from jeepney import DBusAddress, MatchRule, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import open_dbus_connection

from ...l10n import tr
from ..base import DeviceError
from .protocols import uuid16

BLUEZ, DEVICE, CHARACTERISTIC = "org.bluez", "org.bluez.Device1", "org.bluez.GattCharacteristic1"
PROPERTIES, OBJECTS = "org.freedesktop.DBus.Properties", "org.freedesktop.DBus.ObjectManager"
MAX_MESSAGES = 5000  # per listening, as a bound


@dataclass(frozen=True)
class Advert:
    address: str
    name: str
    rssi: int | None
    service_data: dict[int, bytes] = field(default_factory=dict)


def _value(variant, default=None):
    return variant[1] if variant else default


class Bluez:
    """One connection to the system bus and the first adapter on it."""

    def __init__(self):
        try:
            self._bus = open_dbus_connection(bus="SYSTEM")
        except (OSError, ConnectionError) as error:
            raise DeviceError(tr("Bluetooth is not available: {error}", error=error)) from error
        self.adapter = next((path for path, ifaces in self._objects().items()
                             if "org.bluez.Adapter1" in ifaces), None)
        if self.adapter is None:
            self.close()
            raise DeviceError(tr("No Bluetooth adapter was found."))
        self._names: dict[str, str] = {}

    def close(self) -> None:
        self._bus.close()

    def _call(self, path: str, interface: str, method: str, signature: str = "", body=(),
              timeout: float = 10.0):
        address = DBusAddress(path, bus_name=BLUEZ, interface=interface)
        message = new_method_call(address, method, signature, body)
        try:
            reply = self._bus.send_and_get_reply(message, timeout=timeout)
        except TimeoutError as error:
            raise DeviceError(tr("The sensor did not answer.")) from error
        if reply.header.message_type.name == "error":
            raise DeviceError(str(reply.body[0] if reply.body else reply.header.fields.get(4)))
        return reply.body

    def _objects(self) -> dict:
        return self._call("/", OBJECTS, "GetManagedObjects")[0]

    def _watch(self, **rule) -> None:
        self._bus.send_and_get_reply(message_bus.AddMatch(MatchRule(type="signal", sender=BLUEZ,
                                                                    **rule)))

    def find(self, seconds: float, wanted) -> Advert | None:
        """The first advertisement `wanted` accepts, heard within `seconds`; listening ends
        before it is returned, so a connection can follow."""
        heard = self.listen(seconds)
        try:
            return next((advert for advert in heard if wanted(advert)), None)
        finally:
            heard.close()

    def listen(self, seconds: float) -> Iterator[Advert]:
        """The advertisements heard within `seconds`, as they arrive. Closing the iterator
        ends listening."""
        known = self._objects()
        self._names.update({path: _value(ifaces[DEVICE].get("Name"), "")
                            for path, ifaces in known.items() if DEVICE in ifaces})
        self._watch(interface=PROPERTIES, member="PropertiesChanged", path_namespace=self.adapter)
        self._watch(interface=OBJECTS, member="InterfacesAdded")
        self._call(self.adapter, "org.bluez.Adapter1", "SetDiscoveryFilter", "a{sv}",
                   ({"Transport": ("s", "le"), "DuplicateData": ("b", True)},))
        self._call(self.adapter, "org.bluez.Adapter1", "StartDiscovery")
        end = time.monotonic() + seconds
        try:
            for _ in range(MAX_MESSAGES):
                left = end - time.monotonic()
                if left <= 0:
                    return
                try:
                    message = self._bus.receive(timeout=left)
                except TimeoutError:
                    return
                advert = self._advert(message)
                if advert is not None:
                    yield advert
        finally:
            self._call(self.adapter, "org.bluez.Adapter1", "StopDiscovery")

    def _advert(self, message) -> Advert | None:
        member, path = message.header.fields.get(3), message.header.fields.get(1, "")
        if member == "InterfacesAdded":
            path, interfaces = message.body
            props = interfaces.get(DEVICE)
        elif member == "PropertiesChanged" and message.body[0] == DEVICE:
            props = message.body[1]
        else:
            return None
        if props is None:
            return None
        if "Name" in props:
            self._names[path] = _value(props["Name"], "")
        data = {uuid16(uuid): bytes(value) for uuid, (_, value) in
                _value(props.get("ServiceData"), {}).items() if uuid16(uuid) is not None}
        address = path.rsplit("/dev_", 1)[-1].replace("_", ":")
        return Advert(address, self._names.get(path, ""), _value(props.get("RSSI")), data)

    def device(self, address: str) -> str:
        return f"{self.adapter}/dev_{address.replace(':', '_')}"

    def connect(self, address: str) -> None:
        """Connects and waits until the services of the device are resolved; before that
        its characteristics may be known from a cache but cannot be used."""
        path = self.device(address)
        self._call(path, DEVICE, "Connect", timeout=25.0)
        for _ in range(40):
            resolved = self._call(path, PROPERTIES, "Get", "ss", (DEVICE, "ServicesResolved"))
            if _value(resolved[0], False):
                return
            time.sleep(0.25)
        raise DeviceError(tr("The sensor did not answer."))

    def disconnect(self, address: str) -> None:
        try:
            self._call(self.device(address), DEVICE, "Disconnect", timeout=10.0)
        except DeviceError:
            pass

    def characteristic(self, address: str, uuid: str) -> str:
        """The object path of a characteristic, waiting up to 10 s for its discovery."""
        prefix = self.device(address) + "/"
        for _ in range(20):
            for path, ifaces in self._objects().items():
                found = ifaces.get(CHARACTERISTIC)
                if path.startswith(prefix) and found and _value(found["UUID"]).lower() == uuid:
                    return path
            time.sleep(0.5)
        raise DeviceError(tr("The sensor does not offer the service needed."))

    def read(self, path: str) -> bytes:
        return bytes(self._call(path, CHARACTERISTIC, "ReadValue", "a{sv}", ({},))[0])

    def write(self, path: str, data: bytes) -> None:
        self._call(path, CHARACTERISTIC, "WriteValue", "aya{sv}",
                   (data, {"type": ("s", "request")}))

    def ask(self, path: str, data: bytes, seconds: float = 5.0) -> bytes:
        """Writes a command and waits for the notification that answers it. The filter is
        set before the write, since the answer may come before the write is acknowledged."""
        self._watch(interface=PROPERTIES, member="PropertiesChanged", path=path)
        # Locally the signal carries the unique name of BlueZ, not its well-known one.
        local = MatchRule(type="signal", interface=PROPERTIES, member="PropertiesChanged",
                          path=path)
        with self._bus.filter(local) as queue:
            self._call(path, CHARACTERISTIC, "StartNotify")
            try:
                self.write(path, data)
                end = time.monotonic() + seconds
                for _ in range(MAX_MESSAGES):
                    left = end - time.monotonic()
                    if left <= 0:
                        break
                    try:
                        message = self._bus.recv_until_filtered(queue, timeout=left)
                    except TimeoutError:
                        break
                    value = message.body[1].get("Value") if len(message.body) > 1 else None
                    answer = bytes(value[1]) if value else b""
                    if answer[:1] == data[:1]:
                        return answer
                raise DeviceError(tr("The sensor did not answer."))
            finally:
                self._call(path, CHARACTERISTIC, "StopNotify")
