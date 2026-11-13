# OkeyDocu - tools/panel-svg.py
# Draws the front panel of the PROFITEST PRIME as SVG: sockets, display with keys, dial.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run from the checkout: `python3 tools/panel-svg.py`. Writes `front.svg` and `knob.svg` next
to the driver. Every part a guide points at carries an id: `socket-1`, `key-start`, `soft-1`,
`led-mains`, `pos-18` for a dial position by the value the instrument reports, and so on.
The knob is a drawing of its own, pointing up, so it can be turned in front of the panel."""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from okeydocu.devices.profitest_prime.panel import DIAL, STEP_DEGREES as STEP  # noqa: E402

OUT = ROOT / "okeydocu/devices/profitest_prime/panel"
WIDTH, HEIGHT = 1180, 600

PANEL, METAL, INK, GREEN, DIM = "#2c3037", "#b9bec4", "#f2f4f5", "#3ec46d", "#7d848b"
SINE = "M-11,0 C-8,-9 -3,-9 0,0 S8,9 11,0"
ICONS = {
    "step": '<path d="M-11,6 h8 v-12 h14" fill="none" stroke="{c}" stroke-width="2"/>',
    "ramp": '<path d="M-11,7 L11,7 L11,-7 Z" fill="{c}"/>',
    "sine": f'<path d="{SINE}" fill="none" stroke="{{c}}" stroke-width="2"/>',
    "sine2": f'<path d="{SINE}" fill="none" stroke="{{c}}" stroke-width="2"/>'
             '<path d="M-11,6 L11,-6" stroke="{c}" stroke-width="1.5"/>',
    "pulse": '<path d="M-11,6 v-12 h5 v12 h4 v-12 h5 v12" fill="none" stroke="{c}"'
             ' stroke-width="2"/>',
    "battery": '<rect x="-12" y="-7" width="22" height="14" rx="2" fill="none" stroke="{c}"'
               ' stroke-width="2"/><rect x="10" y="-3" width="3" height="6" fill="{c}"/>'
               '<path d="M1,-6 L-4,1 L0,1 L-2,6 L4,-1 L0,-1 Z" fill="{c}"/>',
}
# Physical position (0 is OFF at the top, clockwise) to the value the instrument reports,
# its text and an optional symbol beside the text.
POSITIONS = [
    (0, 35, "OFF", None), (1, 12, "U", None), (2, 13, "0,2A", None), (3, 14, "25A", None),
    (4, 15, "", "step"), (5, 16, "", "ramp"), (6, 17, "IF◢", None), (7, 18, "IΔN", None),
    (8, 19, "IF◢+IΔN", None), (9, 20, "", "sine"), (10, 21, "DC+", "sine"),
    (11, 22, "", "sine2"), (12, 23, "", "pulse"), (13, 24, "Ures", None),
    (14, 25, "IMD", None), (15, 26, "RCM", None), (16, 27, "IL", None),
    (17, 28, "≤1V≂", None), (18, 29, "T, %r.H.", None), (19, 30, "Extra", None),
    (20, 31, "HV", None), (21, 32, "Auto", None), (22, 33, "Setup", None),
    (23, 34, "", "battery"),
]
GROUPS = [("RLO", 2, 3), ("RISO", 4, 5), ("RCD", 6, 8), ("ZLOOP AC/DC", 9, 12)]


def polar(radius: float, position: float) -> tuple[float, float]:
    angle = math.radians(position * STEP)
    return DIAL[0] + radius * math.sin(angle), DIAL[1] - radius * math.cos(angle)


def text(x, y, words, size=13, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y + size * 0.36:.1f}" font-family="sans-serif"'
            f' font-size="{size}" fill="{color}" text-anchor="{anchor}"'
            f' font-weight="{weight}">{words}</text>')


def dial() -> list[str]:
    parts = [f'<circle cx="{DIAL[0]}" cy="{DIAL[1]}" r="104" fill="none" stroke="{GREEN}"'
             ' stroke-width="7" stroke-dasharray="20 7.23" transform="rotate(-95.5 '
             f'{DIAL[0]} {DIAL[1]})"/>']
    for physical, value, words, icon in POSITIONS:
        x, y = polar(132, physical)
        color = DIM if value == 31 else INK
        body = []
        if words:
            body.append(text(0, 0 if not icon else -9, words, 12, color))
        if icon:
            body.append(f'<g transform="translate(0,{8 if words else 0})">'
                        + ICONS[icon].format(c=color) + "</g>")
        parts.append(f'<g id="pos-{value}" transform="translate({x:.1f},{y:.1f})">'
                     + "".join(body) + "</g>")
    for label, first, last in GROUPS:
        x1, y1 = polar(166, first - 0.4)
        x2, y2 = polar(166, last + 0.4)
        parts.append(f'<path d="M{x1:.1f},{y1:.1f} A166,166 0 0 1 {x2:.1f},{y2:.1f}"'
                     f' fill="none" stroke="{GREEN}" stroke-width="1.5"/>')
        x, y = polar(182, (first + last) / 2)
        parts.append(text(x, y, label, 11, GREEN))
    return parts


def keys() -> list[str]:
    parts = [f'<rect x="318" y="238" width="392" height="314" rx="10" fill="none"'
             f' stroke="{METAL}" stroke-width="2"/>']
    leds = [("led-mains", "MAINS NETZ"), ("led-batt", "BATT"), ("led-ul", "UL/RL"),
            ("led-rcd", "RCD FI")]
    for index, (key, label) in enumerate(leds):
        x = 352 + index * 92
        parts.append(f'<circle id="{key}" cx="{x}" cy="262" r="7" fill="#55595e"'
                     f' stroke="{METAL}"/>')
        parts.append(text(x + 12, 262, label, 10, INK, "start"))
    parts.append('<rect id="lcd" x="452" y="284" width="148" height="252" rx="4"'
                 ' fill="#c9cfb8" stroke="#8b927c" stroke-width="2"/>')
    for index, (key, label) in enumerate([("key-esc", "ESC"), ("key-mem", "MEM"),
                                          ("key-help", "HELP"), ("key-start", "ON START"),
                                          ("key-idn", "IΔN")]):
        y = 296 + index * 50
        parts.append(f'<rect id="{key}" x="330" y="{y}" width="56" height="30" rx="4"'
                     ' fill="#1b1e22" stroke="#55595e" stroke-width="2"/>')
        parts.append(text(394, y + 15, label, 11, GREEN if key == "key-start" else INK,
                          "start"))
    for index in range(5):
        y = 296 + index * 50
        parts.append(f'<rect id="soft-{index + 1}" x="640" y="{y}" width="56" height="30"'
                     ' rx="4" fill="#1b1e22" stroke="#55595e" stroke-width="2"/>')
        parts.append(f'<path d="M604,{y + 15} H636" stroke="{METAL}" stroke-width="1.5"/>')
    return parts


def sockets() -> list[str]:
    parts = [f'<circle id="socket-clamp" cx="118" cy="214" r="24" fill="#1b1e22"'
             f' stroke="{METAL}" stroke-width="3"/>',
             '<circle id="led-warning" cx="118" cy="262" r="8" fill="#e8a33d"/>',
             f'<rect x="40" y="290" width="250" height="24" fill="{METAL}"/>',
             text(280, 302, "Electrical TEST", 12, "#2c3037", "end")]
    for index, label in enumerate(["1(L)", "2(N)", "3(PE)"]):
        y = 352 + index * 74
        row = [f'<circle cx="{x}" cy="{y}" r="17" fill="#1b1e22" stroke="{METAL}"'
               ' stroke-width="3"/>' for x in (70, 120)]
        row.append(f'<circle cx="182" cy="{y}" r="25" fill="#1b1e22" stroke="{METAL}"'
                   ' stroke-width="3"/>')
        row.append(text(222, y + 22, label, 16, INK, "start", "bold"))
        parts.append(f'<g id="socket-{index + 1}">' + "".join(row) + "</g>")
    return parts


def mains() -> list[str]:
    parts = [f'<rect x="40" y="110" width="860" height="70" fill="{METAL}"/>',
             '<rect id="mains-inlet" x="952" y="24" width="64" height="52" rx="4"'
             ' fill="#1b1e22" stroke="#55595e" stroke-width="2"/>',
             '<rect id="mains-switch" x="1036" y="24" width="34" height="52" rx="4"'
             ' fill="#c0392b" stroke="#55595e" stroke-width="2"/>',
             text(1011, 92, "115/230 V~", 11),
             '<rect id="fuses" x="940" y="108" width="196" height="118" rx="4"'
             ' fill="#1b1e22" stroke="#55595e" stroke-width="2"/>']
    for index in range(4):
        x = 954 + index * 46
        parts.append(f'<rect id="fuse-{index + 1}" x="{x}" y="140" width="36" height="74"'
                     f' rx="3" fill="#3a3f45" stroke="{METAL}"/>')
        parts.append(text(x + 18, 124, f"F{index + 1}", 10))
    parts += ['<rect id="usb" x="742" y="200" width="30" height="24" rx="3"'
              f' fill="{METAL}" stroke="#55595e"/>', text(757, 238, "USB", 10),
              '<path id="rs232" d="M792,198 h70 l-6,28 h-58 Z"'
              f' fill="{METAL}" stroke="#55595e"/>', text(827, 238, "RS 232", 10)]
    return parts


def front() -> str:
    body = mains() + sockets() + keys() + dial()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}">\n'
            '<!-- SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck'
            ' <thorsten.schnebeck@gmx.net> -->\n'
            '<!-- SPDX-License-Identifier: GPL-3.0-or-later -->\n'
            '<!-- Written by tools/panel-svg.py. -->\n'
            f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="28" fill="{PANEL}"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def knob() -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -100 200 200">\n'
            '<!-- SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck'
            ' <thorsten.schnebeck@gmx.net> -->\n'
            '<!-- SPDX-License-Identifier: GPL-3.0-or-later -->\n'
            '<!-- Written by tools/panel-svg.py; it points up and turns about 0,0. -->\n'
            '<circle r="92" fill="#111315" stroke="#3a3f45" stroke-width="4"/>\n'
            '<circle r="70" fill="#1d2024"/>\n'
            '<rect x="-17" y="-88" width="34" height="176" rx="14" fill="#2a2e33"'
            ' stroke="#45494f" stroke-width="2"/>\n'
            f'<rect x="-3" y="-80" width="6" height="26" rx="3" fill="{GREEN}"/>\n'
            '</svg>\n')


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "front.svg").write_text(front(), encoding="utf-8")
    (OUT / "knob.svg").write_text(knob(), encoding="utf-8")
    print("written:", OUT / "front.svg", OUT / "knob.svg")
