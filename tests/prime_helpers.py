# OkeyDocu - tests/prime_helpers.py
# Synthetic replies, events and databases of the PROFITEST PRIME, and a fake instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import queue
import threading

OHM = "Ω"  # what the instrument really sends


def reply(command, data=b"", error=0):
    digest = hashlib.md5(data).hexdigest()
    return (
        f"<reply>\n  <command><![CDATA[{command}]]></command>\n"
        '  <data type="ASCII"><![CDATA['.encode()
        + data
        + f"]]></data>\n  <md5>{digest}</md5>\n  <error>{error}</error>\n</reply>\n".encode()
    )


def empty_reply(command):
    return (
        f"<reply><command><![CDATA[{command}]]></command><data type=\"ASCII\"></data>"
        "<md5 /><error>0</error></reply>"
    ).encode()


def boolean_reply(command, value):
    data = b"true" if value else b"false"
    return (
        f"<reply><command><![CDATA[{command}]]></command><data type=\"boolean\">".encode()
        + data
        + f"</data><md5>{hashlib.md5(data).hexdigest()}</md5><error>0</error></reply>".encode()
    )


def event(guid="00000000-0000-1000-8000-00000000000a", value="&gt;1.20G" + OHM):
    return (
        '<Event xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://example.org/Common-Event-xml" origin="PushPrint" name="OnSavePressed"'
        ' timestamp="2026-02-01T09:00:00"><EventArgs>'
        f'<MEASUREMENT comment="" completed="true" guid="{guid}" id="" passed="true"'
        ' testdate="2026-01-01T09:00:00.000" tester="Prüfer" txt="" type="TS1165">'
        '<TRANSLATEABLEPARAMETER description="TS1245" value="TS1438"></TRANSLATEABLEPARAMETER>'
        f'<RESULT lowerlimit="&gt;1.00M{OHM}" passed="true" value="{value}" variable="TS1165">'
        '</RESULT><RESULT passed="true" value="519V" variable="TS1170"></RESULT>'
        "</MEASUREMENT></EventArgs></Event>"
    ).encode()


class FakeInstrument:
    """A channel with an instrument behind it."""

    def __init__(self, push_on=False, serial_no=b"TEST0001"):
        self.sent = []
        self.push_on = push_on
        self.serial_no = serial_no
        self.incoming = queue.Queue()
        self.broken = False
        self.closed = False
        self.lock = threading.Lock()
        self.wheel = b"0;15\n"
        self.refuse_push = 0

    def read(self):
        if self.broken:
            raise OSError("verbindung weg")
        try:
            return self.incoming.get(timeout=0.01)
        except queue.Empty:
            return b""

    def write(self, data):
        if self.broken:
            raise OSError("verbindung weg")
        command = data.decode().strip()
        self.sent.append(command)
        if command == "PPXML:IS:ON":
            self.incoming.put(boolean_reply(command, self.push_on))
        elif command == "SYS:GET:ROTATIONWHEEL":
            self.incoming.put(self.wheel)
        elif command == "PPXML:ENTER" and self.refuse_push:
            self.incoming.put(reply(command, error=self.refuse_push))
        elif command in ("PPXML:ENTER", "PPXML:LEAVE"):
            self.push_on = command == "PPXML:ENTER"
            self.incoming.put(empty_reply(command))
        elif command == "IDNXML:GET:SERIALNO":
            self.incoming.put(reply(command, self.serial_no))
        else:
            self.incoming.put(reply(command, b"M506A"))

    def close(self):
        self.closed = True

    def press_save(self, *args, **kwargs):
        self.incoming.put(event(*args, **kwargs))


DATABASE = """<?xml version="1.0" encoding="UTF-8"?>
<PROFITEST date="2026-01-01T10:00:00.000" version="01.07.00">
<TESTDEVICE calibdate="2026-01-10" firmware="01.02.03" hardware="A01"
 manufacturer="GOSSEN METRAWATT" orderno="M506A" recalibdate="2027-01-10"
 serialno="TEST0001" type="PROFITEST PRIME"></TESTDEVICE>
<DATABASE><CUSTOMER guid="c" id="K1" txt="Kunde"><MACHINE guid="m" id="M1" txt="Maschine">
<DISTRIBUTIONCABINET guid="d" id="S1" txt="Schrank">
<MEASUREMENT comment="" completed="true" guid="g-riso" passed="true"
 testdate="2026-01-01T09:00:05.000" tester="Prüfer" type="TS1165">
<RANGEDPARAMETER description="TS1250" value="500V"></RANGEDPARAMETER>
<RESULT lowerlimit="&gt;1.00MΩ" passed="true" value="2.05MΩ" variable="TS1165"></RESULT>
<RESULT passed="true" value="519V" variable="TS1170"></RESULT>
</MEASUREMENT>
<MEASUREMENT completed="true" guid="g-z" passed="true"
 testdate="2026-01-01T09:01:00.000" tester="Prüfer" type="TS1607">
<RESULT passed="true" value="3.76kA" variable="TS1355"></RESULT>
<RESULT passed="false" value="230V" variable="TS1350"></RESULT>
</MEASUREMENT>
<MEASUREMENT completed="true" guid="g-bad" passed="false"
 testdate="2026-01-01T09:02:00.000" tester="Prüfer" type="TS9999">
<RESULT lowerlimit="&gt;1.00MΩ" passed="false" value="0.50MΩ" variable="TS8888"></RESULT>
</MEASUREMENT>
</DISTRIBUTIONCABINET></MACHINE></CUSTOMER></DATABASE></PROFITEST>
""".encode()
ADDRESS = "00:11:22:33:44:55"
