# OkeyDocu - tests/izytron_helpers.py
# An invented IZYTRON database for the import tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import sqlite3

DEVICE = json.dumps({
    "DeviceType": "PROFITEST PRIME", "Manufacturer": "GOSSEN METRAWATT",
    "SerialNumber": "TEST0001", "LastCalibrationDate": "2023-03-01T12:00:00",
})


def value(number, unit, prefix=None, precision=2, ranger=0):
    return {"Value": number, "Unit": unit, "Prefix": prefix, "Precision": precision,
            "RangerResult": ranger}


def measurement(key, description, reading, minimum=None, maximum=None, beside=(), **extra):
    return {
        "MainMeasurements": [{
            "TsKey": f"PROFITEST_{key}", "Description": description, "Value": reading,
            "Min": minimum, "Max": maximum, "Result": 0, "BesideMeasurements": list(beside),
            **extra,
        }],
        "Parameters": [
            {"Name": "RISO - Leiter", "Value": "L1-PE", "TsKey": "PROFITEST_TS1245"},
            {"Name": "RISO - Nennspannung", "Value": "500 V", "TsKey": "PROFITEST_TS1250"},
        ],
    }


def build(path):
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE Hierarchical_Object (ID TEXT, Designation TEXT, Designation2 TEXT, Object_ID TEXT,
        Object_Type INT, Parent_ID TEXT, Deleted INT DEFAULT 0);
    CREATE TABLE Customer (ID TEXT, Designation TEXT, Street TEXT, Postal_Code TEXT, City TEXT,
        Deleted INT DEFAULT 0);
    CREATE TABLE Abstract_Device (ID TEXT, Type TEXT, Serial_Number TEXT, Manufacturer TEXT,
        Remark TEXT, Department TEXT, Cost_Center TEXT);
    CREATE TABLE Contact (ID TEXT, Salutation TEXT, Title TEXT, First_Name TEXT, Last_Name TEXT,
        Department TEXT, Phone_Number TEXT, Email_Address TEXT, Mobile_Phone_Number TEXT,
        Is_Active INT, Customer_ID TEXT, Deleted INT DEFAULT 0);
    CREATE TABLE Testing_Device (Serial_Number TEXT, Next_Inspection TEXT);
    CREATE TABLE Testing (ID TEXT, Abstract_Device_ID TEXT, Date TEXT, Name TEXT, Kind TEXT,
        Tester_Name TEXT, Deleted INT DEFAULT 0);
    CREATE TABLE Testing_Step (ID TEXT, Testing_ID TEXT, Has_Passed INT, Step_Number INT,
        Measurement_Data TEXT, Testing_Device_Information TEXT, Comment TEXT,
        Deleted INT DEFAULT 0, Step_Description TEXT);
    """)
    db.execute("INSERT INTO Customer VALUES ('C','Muster AG','Weg 1','12345','Musterstadt',0)")
    # GUIDs differ in case between tables, and the child row comes first.
    rows = [
        ("h3", "Schrank", "EC1", "DIST", 232, "h2", 0),
        ("h2", "Presse", "M1", "mach", 231, "h1", 0),
        ("h1", "Muster AG", "K1", "C", 210, None, 0),
        ("h4", "Gelöscht", "X", "gone", 242, "h3", 1),
        ("h5", "Punkt", "MP1", "POINT", 242, "h3", 0),
    ]
    db.executemany("INSERT INTO Hierarchical_Object VALUES (?,?,?,?,?,?,?)", rows)
    db.execute("INSERT INTO Abstract_Device VALUES"
               " ('MACH','Typ X','S-1','Hersteller','','Instandhaltung','4711')")
    db.executemany("INSERT INTO Contact VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("P1", "Herr", "", "Max", "Alt", "", "0123 1111", "", "", 0, "c", 0),  # left the firm
        ("P2", "Frau", "Dr.", "Erika", "Muster", "Werkstatt", "", "muster@kunde.example",
         "0170 2222", 1, "c", 0),
    ])
    db.execute("INSERT INTO Testing_Device VALUES ('TEST0001','2024-09-01T00:00:00')")

    def test(id_, target, when, name, kind, data, passed=1, comment=None, deleted=0, step=""):
        db.execute("INSERT INTO Testing VALUES (?,?,?,?,?,?,?)",
                   (id_, target, when, name, kind, "A. Prüfer", deleted))
        db.execute("INSERT INTO Testing_Step VALUES (?,?,?,1,?,?,?,0,?)",
                   (f"S-{id_}", id_.lower(), passed, json.dumps(data), DEVICE, comment, step))

    device = "CommonImportFromDevice"
    test("T1", "dist", "2026-05-04 11:00:00", "RISO", device, measurement(
        "TS1165", "RISO", value(1.2, "Ω", "G", 2, 1),
        minimum=value(1.0, "Ω", "M"),
        beside=[{"TsKey": "PROFITEST_TS1170", "Value": value(519, "V", precision=0), "Result": 0}],
    ))
    test("T2", "point", "2026-05-04 11:01:00", "RLO", device, measurement(
        "TS1358", "RLO", value(0.21, "Ω"), maximum=value(1.0, "Ω"),
    ))
    test("T3", "DIST", "2026-05-04 11:02:00", "U", device, {
        "MainMeasurements": [{
            "TsKey": None, "Value": None, "VerificationValue": "rechts", "Result": 0,
            "BesideMeasurements": [
                {"TsKey": "PROFITEST_TS1371", "Value": value(398, "V", precision=0), "Result": 0},
            ],
        }],
    })
    test("T4", "dist", "2026-05-04 11:03:00", "RLO", device, measurement(
        "TS1358", "RLO", value(199, "Ω", precision=0, ranger=1), maximum=value(1.0, "Ω"),
    ), passed=0)
    test("T5", "dist", "2026-05-04 10:30:00.1234567", "Sichtprüfung der Betriebsmittel",
         "Sichtprüfung",
         {"VisualInspections": [{"Question": "Sind Warnhinweise angebracht?", "Result": True}]},
         comment="Am Schrank innen", step="Warnhinweise")
    # A second question of the same visual inspection: one testing, two steps.
    db.execute("INSERT INTO Testing_Step VALUES ('S-T5b','t5',0,2,?,?,NULL,0,'Schutzleiter')",
               (json.dumps({"VisualInspections": [
                   {"Question": "Ist der Schutzleiter angeschlossen?", "Result": False}]}),
                DEVICE))
    test("T6", "dist", "2026-05-04 11:04:00", "RLO", device, {}, deleted=1)
    db.commit()
    db.close()
