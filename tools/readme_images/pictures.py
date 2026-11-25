# OkeyDocu - tools/readme_images/pictures.py
# Stand-ins for photos: parts of the drawn test objects on a plain ground.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""No photo of a real installation goes into the README. What a camera would be pointed at is
cut out of the drawings of the guided measurement and given the time a photo would carry."""
from datetime import timedelta

from PIL import Image

EXIF_IFD = 0x8769
EXIF_DATETIME_ORIGINAL = 36867
FACTOR = 3  # the sources are drawn at three times the size the parts are given in
# Parts of the measuring window at 1440 by 960, as left, top, right, bottom.
PARTS = {"switch": (118, 705, 252, 852), "dial": (735, 418, 935, 612),
         "rcd": (300, 700, 560, 890), "bar": (300, 700, 760, 890),
         "panel": (485, 415, 735, 575)}
GROUNDS = {"switch": (226, 229, 232), "dial": (70, 78, 88), "rcd": (243, 244, 246),
           "bar": (243, 244, 246), "panel": (70, 78, 88)}
FROM_DIAL = ("switch", "rcd", "bar")  # drawn there without probes
# What is photographed along the round: part, minute and second after its start.
TAKEN = (("switch", 0, 25), ("dial", 3, 40), ("panel", 6, 20), ("bar", 6, 55), ("rcd", 15, 20))


def photo(sources, part, path, moment, size=(1600, 1200)):
    source = sources["dial" if part in FROM_DIAL else "leads"]
    box = tuple(FACTOR * edge for edge in PARTS[part])
    cut = Image.open(source).convert("RGB").crop(box)
    scale = min(size[0] * 0.72 / cut.width, size[1] * 0.72 / cut.height)
    cut = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.LANCZOS)
    image = Image.new("RGB", size, GROUNDS[part])
    image.paste(cut, ((size[0] - cut.width) // 2, (size[1] - cut.height) // 2))
    exif = image.getexif()
    exif.get_ifd(EXIF_IFD)[EXIF_DATETIME_ORIGINAL] = moment.strftime("%Y:%m:%d %H:%M:%S")
    image.save(path, quality=90, exif=exif)
    return path


def series(sources, folder, start, ahead_s=150):
    """Five photos taken along the round of measurements, by a camera running ahead."""
    return [photo(sources, part, folder / f"IMG_{number:04d}.jpg",
                  start + timedelta(minutes=minute, seconds=second + ahead_s))
            for number, (part, minute, second) in enumerate(TAKEN, start=1)]
