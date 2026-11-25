# OkeyDocu - tools/readme_images/demo.py
# l10n: de
# Invented data for the pictures of the README, in English or German.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""One customer with one machine and its parts, an inspector, two ended campaigns and one
under way. Every name is made up; the instrument is a PROFITEST PRIME with a serial number
that does not exist."""
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from okeydocu.campaign import filing
from okeydocu.devices import LiveReading
from okeydocu.model import (DeviceIdentity, MeterMeasurement, Parameter, Quantity, ResultValue,
                            Verdict)

DRIVER = "profitest-prime"
DAY = datetime(2026, 11, 24, 9, 0)
IDENTITY = DeviceIdentity("GOSSEN METRAWATT", "PROFITEST PRIME", "XX000000", "1.0.0", "",
                          "", date(2026, 3, 2), date(2027, 3, 2))

WORDS = {
    "en": dict(customer="Example Manufacturing Ltd", city="Sampletown", street="2 Factory Road",
               machine="Hydraulic press HP-200", cabinet="Control cabinet", drive="Main drive",
               pump="Hydraulic pump", rcd="RCD sockets", sockets="Service sockets",
               panel="Operator panel", user="Alex Example", maker="Example Presses",
               company="Example Testing Services", company_street="1 Sample Street",
               now="Annual inspection 2026", last="Annual inspection 2025",
               between="Inspection after conversion", contact="Kim Sample",
               department="Maintenance", pattern="Hydraulic press, electrical"),
    "de": dict(customer="Beispiel Fertigung GmbH", city="Musterstadt", street="Werkstraße 2",
               machine="Hydraulikpresse HP-200", cabinet="Schaltschrank", drive="Hauptantrieb",
               pump="Hydraulikpumpe", rcd="FI Steckdosen", sockets="Servicesteckdosen",
               panel="Bedienpanel", user="Alex Beispiel", maker="Beispiel Pressen",
               company="Beispiel Prüfdienst", company_street="Musterstraße 1",
               now="Jahresprüfung 2026", last="Jahresprüfung 2025",
               between="Prüfung nach Umbau", contact="Kim Muster",
               department="Instandhaltung", pattern="Hydraulikpresse, elektrisch"),
}

RCD_SET = (Parameter("rated_residual_current", "30mA"), Parameter("rated_current", "40A"),
           Parameter("rcd_type", "A"))
# The round of an inspection: where each measurement is taken, in the order measured.
ROUND = (("machine", "rlo"), ("drive", "riso"), ("pump", "riso"), ("panel", "rlo"),
         ("rcd", "rcd_touch"), ("rcd", "rcd_time"), ("sockets", "zloop"), ("machine", "u3"))


def value(key, label, text, lower="", upper="", verdict=Verdict.PASSED):
    return ResultValue(key, label, Quantity.parse(text), verdict, lower, upper)


def stated(key, label, text):
    """A value the instrument reports without judging it."""
    return value(key, label, text, verdict=Verdict.NOT_EVALUATED)


def readings(function, number=0):
    """What the instrument sends for one measurement of this kind; `number` varies it."""
    return {
        "rlo": [value("rlo", "RLO", f"{70 + 30 * number}mΩ", "", "<300mΩ")],
        "riso": [value("riso", "RISO", f"{761 - 37 * number}MΩ", ">1.00MΩ"),
                 stated("u_iso", "UISO", f"{526 - number}V")],
        "rcd_touch": [value("u_idn", "UIΔN", "2.2V", "", "<50V"), stated("u_ln", "UL-N", "230V")],
        "rcd_time": [value("ta", "ta", "24ms", ">0ms", "<300ms"),
                     stated("u_ln", "UL-N", "230V")],
        "zloop": [stated("zloop", "Z-AC", "410mΩ"), stated("ik", "IK", "0.56kA"),
                  stated("u_ln", "UL-N", "230V")],
        "u3": [stated("u_l1l2", "UL1L2", "401V"), stated("u_l2l3", "UL2L3", "399V"),
               stated("u_l3l1", "UL3L1", "400V")],
    }[function]


def take(app, campaign, asset, function, at, number=0, parameters=()):
    """A reading pushed by the instrument, booked on `asset`."""
    settings = parameters or (RCD_SET if function.startswith("rcd") else ())
    measurement = MeterMeasurement(
        uid=str(uuid.uuid4()), function=function, taken_at=at, verdict=Verdict.PASSED,
        results=tuple(readings(function, number)), parameters=tuple(settings))
    return app.service.receive(campaign, LiveReading(measurement, at), asset)


def plant(app, lang):
    """Customer, structure, inspector and letterhead. Returns the ids by short name."""
    w = WORDS[lang]
    db = app.db
    db.save_company(name=w["company"], street=w["company_street"], zip="12345", city=w["city"])
    ids = {"user": db.add_user(w["user"])}
    customer = db.add_customer(w["customer"], street=w["street"], zip="12345", city=w["city"])
    ids["machine"] = db.add_asset(customer, "machine", w["machine"], identifier="=M10",
                                  manufacturer=w["maker"], type="HP-200")
    db.set_asset_features(ids["machine"], {"nominal_voltage": "400", "rated_current": "32",
                                           "line_conductors": "3", "supply_connection": "fixed"})
    ids["cabinet"] = db.add_asset(customer, "distribution_board", w["cabinet"], ids["machine"],
                                  identifier="+S1")
    for key, power, speed, identifier in (("drive", "15", "1470", "=M1"),
                                          ("pump", "7.5", "1450", "=M2")):
        ids[key] = db.add_asset(customer, "electric_engine", w[key], ids["cabinet"],
                                identifier=identifier)
        db.set_asset_features(ids[key], {"rated_voltage": "400", "rated_power": power,
                                         "speed": speed})
    ids["rcd"] = db.add_asset(customer, "rcd", w["rcd"], ids["cabinet"], identifier="=K1-F1")
    db.set_asset_features(ids["rcd"], {"rcd_type": "A", "number_of_poles": "4",
                                       "rated_residual_current": "30", "rated_current": "40"})
    ids["sockets"] = db.add_asset(customer, "circuit", w["sockets"], ids["rcd"])
    ids["panel"] = db.add_asset(customer, "equipment", w["panel"], ids["machine"],
                                identifier="=A1")
    return ids


def open_campaign(app, ids, title, lang):
    w = WORDS[lang]
    campaign = app.service.create(ids["machine"], title, w["user"], driver_key=DRIVER,
                                  identity=IDENTITY, user_id=ids["user"])
    app.service.set_contact(campaign, w["department"], w["contact"], "", "")
    app.service.set_order(campaign, "", "PO-0000-0001")
    return campaign


def measure_round(app, campaign, ids, start, count=len(ROUND)):
    for number, (place, function) in enumerate(ROUND[:count]):
        take(app, campaign, ids[place], function, start + timedelta(minutes=3 * number), number)


def history(app, ids, lang):
    """Two ended campaigns; the first one becomes the pattern of the next."""
    w = WORDS[lang]
    first = open_campaign(app, ids, w["last"], lang)
    measure_round(app, first, ids, datetime(2025, 11, 18, 9, 0))
    app.service.close(first)
    pattern = app.service.template_from(first, w["pattern"])
    second = open_campaign(app, ids, w["between"], lang)
    measure_round(app, second, ids, datetime(2026, 5, 12, 13, 30))
    app.service.close(second)
    return first, second, pattern


def running(app, ids, lang, pattern, count=5):
    """The campaign of this year, following the pattern, with `count` points taken."""
    campaign = open_campaign(app, ids, WORDS[lang]["now"], lang)
    app.service.use_template(campaign, pattern)
    measure_round(app, campaign, ids, DAY, count)
    app.service.rematch(campaign)
    return campaign


@contextmanager
def clock(moment):
    """What is recorded by hand inside takes this time instead of the present one."""
    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    kept = filing.datetime
    filing.datetime = Fixed
    try:
        yield
    finally:
        filing.datetime = kept


def inspect(app, campaign, plans, answered=0, start=DAY + timedelta(minutes=30)):
    """Adds the inspection of the machine and answers its first questions with yes."""
    plan = next(plan for plan in plans if plan.key == "machine_inspection")
    app.service.assign_plan(campaign, plan)
    block = app.service.plan_blocks(campaign)[-1]
    for number, step_id in enumerate(block.step_ids[:answered]):
        with clock(start + timedelta(seconds=40 * number)):
            app.service.answer_step(step_id, "yes")
    return block
