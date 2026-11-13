# OkeyDocu - tools/panel_parts.py
# The parts of the PROFITEST PRIME's front panel around the dial, for tools/panel-svg.py.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Coordinates are those of the drawing, 1040 by 725, measured off a photo of the instrument
held upright; every part a guide points at carries an id."""

import math

PANEL, METAL, INK, GREEN, DIM = "#2c3037", "#b9bec4", "#f2f4f5", "#3ec46d", "#7d848b"


def text(x, y, words, size=10, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y + size * 0.36:.1f}" font-family="sans-serif"'
            f' font-size="{size}" fill="{color}" text-anchor="{anchor}"'
            f' font-weight="{weight}">{words}</text>')


def key(element, x, y, width=34, height=24):
    return (f'<rect id="{element}" x="{x}" y="{y}" width="{width}" height="{height}" rx="3"'
            ' fill="#1b1e22" stroke="#55595e" stroke-width="1.5"/>')


def line(x1, y1, x2, y2, width=1.5):
    return (f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{METAL}" stroke-width="{width}"'
            ' fill="none"/>')


def display() -> list[str]:
    parts = [f'<rect x="457" y="439" width="313" height="195" rx="5" fill="none"'
             f' stroke="{METAL}" stroke-width="1.5"/>', line(770, 439, 1020, 439),
             line(462, 456, 512, 456, 1), line(712, 456, 764, 456, 1)]
    leds = [("led-mains", "MAINS NETZ", 522, "start"), ("led-batt", "BATT", 585, "start"),
            ("led-ul", "UL/RL", 649, "end"), ("led-rcd", "RCD FI", 673, "start")]
    for element, label, x, anchor in leds:
        parts.append(f'<circle id="{element}" cx="{x}" cy="456" r="4.5" fill="#55595e"'
                     f' stroke="{METAL}"/>')
        parts.append(text(x + (7 if anchor == "start" else -7), 456, label, 6.5, INK, anchor))
    parts.append('<rect id="lcd" x="543" y="472" width="145" height="150" rx="3"'
                 ' fill="#c9cfb8" stroke="#8b927c" stroke-width="1.5"/>')
    names = [("key-esc", "ESC"), ("key-mem", "MEM"), ("key-help", "HELP"),
             ("key-start", "ON START"), ("key-idn", "IΔN")]
    for index, (element, label) in enumerate(names):
        y = 478 + index * 29
        parts.append(key(element, 462, y, 40, 21))
        parts.append(text(506, y + 10, label, 6.5, GREEN if element == "key-start" else INK,
                          "start"))
    for index in range(5):
        y = 478 + index * 29
        parts.append(key(f"soft-{index + 1}", 726, y, 40, 21))
        parts.append(line(694, y + 10, 721, y + 10, 1))
    return parts


def jack(x, y) -> str:
    """A 4 mm safety socket: outer ring, inner ring, bright contact."""
    return (f'<circle cx="{x}" cy="{y}" r="14" fill="#1b1e22" stroke="{METAL}"'
            ' stroke-width="2.5"/>'
            f'<circle cx="{x}" cy="{y}" r="8" fill="#15171a" stroke="#4a4f55"'
            ' stroke-width="1.5"/>'
            f'<circle cx="{x}" cy="{y}" r="3" fill="#e9ebed"/>')


def probe_socket(x, y, mark: str) -> str:
    """The larger socket for a test probe plug, with its grid insert."""
    grid = "".join(f'<path d="M{x + dx},{y - 7} V{y + 7}" stroke="#55595e"'
                   ' stroke-width="1.5"/>' for dx in (-4, 0, 4))
    sign = text(x + 15, y - 14, mark, 8) if mark else ""
    return (f'<circle cx="{x}" cy="{y}" r="16" fill="#1b1e22" stroke="{METAL}"'
            ' stroke-width="2.5"/>'
            f'<circle cx="{x}" cy="{y}" r="10" fill="#26292d"/>' + grid + sign)


def sockets() -> list[str]:
    pins = "".join(f'<circle cx="{314 + 6 * math.cos(a):.1f}" cy="{305 + 6 * math.sin(a):.1f}"'
                   f' r="1.3" fill="{METAL}"/>'
                   for a in [math.radians(d) for d in (-90, -18, 54, 126, 198)])
    parts = [f'<g id="socket-clamp"><circle cx="314" cy="305" r="17" fill="#1b1e22"'
             f' stroke="{METAL}" stroke-width="2.5"/><circle cx="314" cy="305" r="10"'
             f' fill="#26292d" stroke="#55595e"/>{pins}</g>',
             line(322, 320, 428, 320), text(380, 314, "≤1V", 6),
             f'<path d="M392,314 H404" stroke="{INK}" stroke-width="1"/>'
             f'<path d="M401,311.5 L405,314 L401,316.5 Z" fill="{INK}"/>'
             f'<circle cx="411" cy="314" r="5" fill="none" stroke="{INK}"/>'
             f'<path d="M414,309 L418,305 M416,311 L420,308" stroke="{INK}"/>',
             '<circle id="led-warning" cx="313" cy="356" r="5.5" fill="#d9362b"'
             f' stroke="{METAL}"/>',
             f'<rect x="322" y="349" width="106" height="15" fill="none" stroke="{METAL}"'
             ' stroke-width="1"/>', text(421, 356.5, "⚠", 8, INK),
             line(275, 356, 307, 356), line(275, 356, 275, 449),
             f'<rect x="273" y="449" width="147" height="13" fill="{METAL}"/>',
             text(416, 455.5, "Electrical TEST", 7, "#2c3037", "end"),
             text(339, 648, "600V CAT III   300V CAT IV", 6, INK, "start")]
    for index, (label, mark) in enumerate([("1(L)", "+"), ("2(N)", ""), ("3(PE)", "−")]):
        y = 488 + index * 59
        row = [jack(288, y), jack(326, y), probe_socket(367, y, mark),
               line(272, y + 25, 430, y + 25, 1),
               text(400, y + 15, label, 10, INK, "start", "bold")]
        parts.append(f'<g id="socket-{index + 1}">' + "".join(row) + "</g>")
    return parts


def mains() -> list[str]:
    pins = "".join(f'<rect x="{x}" y="58" width="5" height="12" fill="{METAL}"/>'
                   for x in (829, 841.5, 854))
    return ['<rect x="763" y="25" width="175" height="78" rx="3" fill="none"'
            f' stroke="{METAL}" stroke-width="1"/>',
            '<g id="mains-inlet"><path d="M818,40 H870 V78 L862,90 H826 L818,78 Z"'
            ' fill="#1b1e22" stroke="#55595e" stroke-width="2"/>'
            '<path d="M824,48 H864 V76 L858,84 H830 L824,76 Z" fill="#26292d"/>'
            f'{pins}</g>',
            '<g id="mains-switch"><rect x="884" y="50" width="24" height="42" rx="3"'
            ' fill="#c0392b" stroke="#55595e" stroke-width="2"/>'
            '<path d="M886,71 H906" stroke="#8e2a20" stroke-width="1"/>'
            + text(896, 60, "I", 8) + text(896, 82, "O", 8) + "</g>",
            text(790, 52, "115/230 V~", 6), text(790, 62, "50–60 Hz", 6),
            text(790, 76, "2× M3,15/250V", 5.5)]


def fuses() -> list[str]:
    ratings = ["20A/1kV", "10A/1kV", "2A/1kV", "0,44A/1kV"]
    parts = ['<rect id="fuses" x="775" y="140" width="163" height="128" rx="3"'
             ' fill="#1b1e22" stroke="#55595e" stroke-width="1.5"/>',
             text(784, 148, "⚠", 7, INK, "start"),
             text(860, 148, "not under load", 5.5, INK)]
    for index, rating in enumerate(ratings):
        x = 781 + index * 39
        body = (f'<rect x="{x}" y="172" width="34" height="90" rx="2" fill="#3a3f45"'
                f' stroke="{METAL}"/>'
                f'<rect x="{x + 2}" y="174" width="30" height="9" fill="#c8ccd0"/>'
                f'<path d="M{x},222 H{x + 34}" stroke="#55595e" stroke-width="1.5"/>'
                f'<rect x="{x + 6}" y="238" width="8" height="8" fill="#0d0f11"/>'
                f'<rect x="{x + 20}" y="238" width="8" height="8" fill="#0d0f11"/>')
        parts.append(f'<g id="fuse-{index + 1}">{body}</g>')
        parts.append(text(x + 17, 158, rating, 5.5))
        parts.append(text(x + 17, 166, f"F{index + 1}", 6))
    return parts


def top() -> list[str]:
    parts = [f'<rect x="79" y="175" width="696" height="95" fill="{METAL}"/>',
             '<circle id="led-bluetooth" cx="987" cy="173" r="4" fill="#2f7fd8"/>']
    parts += mains() + fuses()
    parts += [line(783, 387, 783, 418), line(788, 387, 788, 418),
              line(962, 387, 962, 418), line(967, 387, 967, 418), line(755, 418, 1020, 418),
              line(788, 387, 962, 387),
              '<g id="usb-symbol" transform="translate(768,404)">'
              f'<circle cx="-9" cy="0" r="1.8" fill="{INK}"/>'
              f'<path d="M-9,0 H7 M-4,0 L-1,-3.5 H3.5 M-1.5,0 L1.5,3.5 H5" fill="none"'
              f' stroke="{INK}" stroke-width="1"/>'
              f'<path d="M7,-2.2 L10.5,0 L7,2.2 Z" fill="{INK}"/>'
              f'<circle cx="4.6" cy="-3.5" r="1.3" fill="{INK}"/>'
              f'<rect x="5" y="2.4" width="2.3" height="2.3" fill="{INK}"/></g>',
              '<g id="usb"><path d="M812,396 L815,392 H829 L832,396 V410 H812 Z"'
              f' fill="{METAL}" stroke="#55595e"/>'
              '<rect x="815" y="395" width="14" height="13" fill="#1b1e22"/>'
              f'<rect x="818.5" y="399" width="7" height="6" fill="{METAL}"/></g>',
              '<path id="rs232" d="M877,391 H930 Q934,391 933.2,395 L929.8,409'
              ' Q929,413 925,413 H882 Q878,413 877.2,409 L873.8,395 Q873,391 877,391 Z"'
              f' fill="{METAL}" stroke="#55595e"/>',
              '<path d="M882,395 H925 L922,409 H885 Z" fill="#3a3f45"/>',
              *[f'<circle cx="{886 + i * 8.75:.2f}" cy="399" r="1.3" fill="#0d0f11"/>'
                for i in range(5)],
              *[f'<circle cx="{890.4 + i * 8.75:.2f}" cy="405" r="1.3" fill="#0d0f11"/>'
                for i in range(4)],
              f'<circle cx="866" cy="402" r="3.5" fill="{METAL}" stroke="#55595e"/>',
              f'<circle cx="941" cy="402" r="3.5" fill="{METAL}" stroke="#55595e"/>',
              text(972, 405, "RS 232", 7, INK, "start"),
              line(20, 696, 1020, 696)]
    return parts
