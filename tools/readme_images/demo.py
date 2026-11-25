# OkeyDocu - tools/readme_images/demo.py
# Data for the pictures of the README: the plant of the test project, with a history.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The pictures show the invented plant of the test project (`okeydocu/testprojects/plant.py`),
measured with a PROFITEST PRIME that stands in for a real one: the campaigns carry its name
and a serial number that does not exist. Two ended campaigns give the overview its history,
and the first of them the pattern the campaign under way follows."""
from datetime import date, datetime

from okeydocu.model import DeviceIdentity
from okeydocu.testprojects import plant as data
from okeydocu.testprojects.plant import (  # noqa: F401 - used by the picture scripts
    DAY,
    WORDS,
    inspect,
    measure_round,
    plant,
    readings,
    stated,
    take,
)

DRIVER = "profitest-prime"
IDENTITY = DeviceIdentity("GOSSEN METRAWATT", "PROFITEST PRIME", "XX000000", "1.0.0", "",
                          "", date(2026, 3, 2), date(2027, 3, 2))


def open_campaign(app, ids, title, lang):
    return data.open_campaign(app, ids, title, lang, DRIVER, IDENTITY)


def history(app, ids, lang):
    """Two ended campaigns; the first one becomes the pattern of the next."""
    words = WORDS[lang]
    first = open_campaign(app, ids, words["last"], lang)
    measure_round(app, first, ids, datetime(2025, 11, 18, 9, 0))
    app.service.close(first)
    pattern = app.service.template_from(first, words["pattern"])
    second = open_campaign(app, ids, words["between"], lang)
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
