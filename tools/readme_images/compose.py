# OkeyDocu - tools/readme_images/compose.py
# Final pictures of the README, composed and reduced, into docs/images.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Puts the pictures taken into docs/images: both languages on one ground, the banner, the
animation of the timeline, and every picture reduced to a palette.

Usage: compose.py <folder with the pictures taken> <repository>"""
import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.join(sys.argv[1], "")
REPO = sys.argv[2]
FONTS = "/usr/share/fonts/truetype/noto/NotoSans-"
NIGHT, DEEP = (12, 22, 38), (24, 44, 70)
ORANGE, INK = (245, 158, 36), (26, 30, 36)
# Pictures taken, by the name the README shows them under.
PLAIN = {"campaign": "campaign-en", "overview": "overview-en", "guide-dial": "guide-dial-en",
         "guide-leads": "guide-leads-en", "photo-marks": "photo-marks-en",
         "settings-check": "settings-check-en", "report": "report-en-1",
         "languages": "languages", "banner": "banner",
         "instruments-head": "instruments-head-en", "sensor-enrol": "sensor-enrol-en",
         "sensor-settle": "sensor-settle-en"}
BULLETS = ("Live readings by Push/Print from the PROFITEST PRIME",
           "Guided measurements on the instrument's own front panel",
           "Campaign templates that learn \u00b7 sealed, signed reports")


def font(style: str, size: int):
    return ImageFont.truetype(f"{FONTS}{style}.ttf", size)


def ground(size) -> Image.Image:
    """A dark ground that lightens towards the lower right."""
    small = Image.new("RGB", (2, 2))
    small.putdata([NIGHT, NIGHT, NIGHT, DEEP])
    return small.resize(size, Image.BICUBIC).convert("RGBA")


def laid(canvas, picture, at, angle=0.0) -> None:
    """The picture on the canvas with a soft shadow, turned by `angle` degrees."""
    picture = picture.convert("RGBA")
    if angle:
        picture = picture.rotate(angle, Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    mask = picture.getchannel("A").point(lambda value: value * 150 // 255)
    shadow.paste((0, 0, 0, 255), (at[0] + 6, at[1] + 14), mask)
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.alpha_composite(picture, at)


def tag(canvas, text: str, at, size=38) -> None:
    draw = ImageDraw.Draw(canvas)
    face = font("Bold", size)
    _, top, right, _ = draw.textbbox((0, 0), text, font=face)
    draw.rounded_rectangle((at[0], at[1], at[0] + right + 36, at[1] + size + 18), 10,
                           fill=ORANGE)
    draw.text((at[0] + 18, at[1] + 9 - top // 2), text, font=face, fill=INK)


def scaled(name: str, width: int) -> Image.Image:
    shot = Image.open(f"{OUT}{name}.png").convert("RGB")
    return shot.resize((width, round(shot.height * width / shot.width)), Image.LANCZOS)


def languages() -> None:
    canvas = ground((1580, 876))
    for lang, at in (("en", (40, 40)), ("de", (220, 450))):
        shot = Image.open(f"{OUT}languages-{lang}.png").convert("RGB")
        shot = shot.crop((0, 0, shot.width, 455))  # ends below a row of the table
        laid(canvas, shot.resize((1320, round(shot.height * 1320 / shot.width)), Image.LANCZOS),
             at)
    tag(canvas, "English", (1376, 66))
    tag(canvas, "Deutsch", (26, 762))
    canvas.convert("RGB").save(OUT + "languages.png")


def icon(size: int) -> Image.Image:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    QGuiApplication.instance() or QGuiApplication([])
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    QSvgRenderer(os.path.join(REPO, "okeydocu/data/icons/okeydocu.svg")).render(painter)
    painter.end()
    image.save(OUT + "icon.png")
    return Image.open(OUT + "icon.png").convert("RGBA")


def banner() -> None:
    canvas = ground((1800, 640))
    laid(canvas, scaled("campaign-en", 790), (812, 44))
    laid(canvas, scaled("guide-leads-en", 640), (915, 262), angle=2.5)
    laid(canvas, scaled("report-en-1", 330), (1415, 96), angle=-5.0)
    canvas.alpha_composite(icon(106), (83, 115))
    draw = ImageDraw.Draw(canvas)
    draw.text((80, 238), "OkeyDocu", font=font("Bold", 100), fill=(255, 255, 255))
    draw.text((84, 360), "Field testing and documentation on the go", font=font("Italic", 31),
              fill=(150, 190, 225))
    for number, line in enumerate(BULLETS):
        y = 436 + 38 * number
        draw.ellipse((86, y + 12, 98, y + 24), fill=(72, 199, 116))
        draw.text((110, y), line, font=font("Regular", 23), fill=(232, 238, 245))
    canvas.convert("RGB").save(OUT + "banner.png")


def reduced(source: str, target: str, colours="") -> None:
    """A picture with a palette: a fraction of the size, and no difference to the eye."""
    options = ["--quality", "88-100"] if not colours else [colours, "--nofs"]
    subprocess.run(["pngquant", *options, "--speed", "1", "--force", "--output", target, source],
                   check=True, timeout=120)


def animation(width=908) -> None:
    """The frames of the timeline as one GIF: all of them in the palette of three."""
    taken = sorted(glob.glob(OUT + "timeline-en-*.png"))
    frames = [Image.open(path).convert("RGB") for path in taken]
    frames = [frame.resize((width, round(frame.height * width / frame.width)), Image.LANCZOS)
              for frame in frames]
    height = frames[0].height
    sheet = Image.new("RGB", (width, height * 3))
    for row, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
        sheet.paste(frame, (0, row * height))
    sheet.save(OUT + "sheet.png")
    reduced(OUT + "sheet.png", OUT + "sheet-palette.png", "255")
    palette = Image.open(OUT + "sheet-palette.png")
    shown = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    pauses = [2000] + [70] * (len(shown) - 2) + [3000]  # rest at the start and at the end
    shown[0].save(os.path.join(REPO, "docs/images/photo-timeline.gif"), save_all=True,
                  append_images=shown[1:], duration=pauses, loop=0, optimize=True, disposal=1)


languages()
banner()
for name, taken in PLAIN.items():
    reduced(f"{OUT}{taken}.png", os.path.join(REPO, f"docs/images/{name}.png"))
animation()
