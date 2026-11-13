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
sys.path.insert(0, str(ROOT / "tools"))
from okeydocu.devices.profitest_prime.panel import DIAL, STEP_DEGREES as STEP  # noqa: E402

from panel_parts import DIM, GREEN, INK, PANEL, display, sockets, text, top  # noqa: E402

OUT = ROOT / "okeydocu/devices/profitest_prime/panel"
WIDTH, HEIGHT = 1040, 725  # measured off a photo of the instrument, upright
RING, LABELS, ARCS = 76, 89, 101  # radii of the detent ring, the labels and the group arcs

# Wave symbols as on the dial: axes through the origin, one sine period starting upwards.
AXES = "M-10,-9 V9 M-10,0 H12"
SINE = "M-10,0 C-8.5,-12 -2.5,-12 1,0 C4.5,12 10.5,12 12,0"
THIN = 'fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"'
ICONS = {
    "step": '<path d="M-11,6 h8 v-12 h14" fill="none" stroke="{c}" stroke-width="2"/>',
    "ramp": '<path d="M-11,7 L11,7 L11,-7 Z" fill="{c}"/>',
    "sine": f'<path d="{AXES} {SINE}" {THIN}/>',
    "sine2": f'<path d="{AXES} {SINE} M-10,0 L12,-7 V0" {THIN}/>',
    "pulse": f'<path d="M-12,6 H-9 V-6 H-4 V6 H-1 V-6 H4 V6 H12" {THIN}/>',
    "battery": '<rect x="-12" y="-7" width="22" height="14" rx="2" fill="none" stroke="{c}"'
               ' stroke-width="2"/><rect x="10" y="-3" width="3" height="6" fill="{c}"/>'
               '<path d="M1,-6 L-4,1 L0,1 L-2,6 L4,-1 L0,-1 Z" fill="{c}"/>',
}
# Physical position (0 is OFF at the top, clockwise) to the value the instrument reports,
# its text and an optional symbol beside the text.
POSITIONS = [
    (0, 35, "OFF", None), (1, 12, "U", None), (2, 13, "0,2A", None), (3, 14, "25A", None),
    (4, 15, "", "step"), (5, 16, "", "ramp"), (6, 17, "IF◢", None), (7, 18, "IΔN", None),
    (8, 19, "IF◢\n+IΔN", None), (9, 20, "", "sine"), (10, 21, "DC+", "sine"),
    (11, 22, "", "sine2"), (12, 23, "", "pulse"), (13, 24, "Ures", None),
    (14, 25, "IMD", None), (15, 26, "RCM", None), (16, 27, "IL", None),
    (17, 28, "≤1V≂", None), (18, 29, "T, %r.H.", None), (19, 30, "Extra", None),
    (20, 31, "HV", None), (21, 32, "Auto", None), (22, 33, "Setup", None),
    (23, 34, "", "battery"),
]
# Each group arc runs between two detents, counted from OFF; its name stands at its end.
GROUPS = [("RLO", 1.6, 3.3), ("RISO", 4.0, 5.1), ("RCD", 5.9, 7.9),
          ("ZLOOP AC/DC", 8.6, 11.9)]


def polar(radius: float, position: float) -> tuple[float, float]:
    angle = math.radians(position * STEP)
    return DIAL[0] + radius * math.sin(angle), DIAL[1] - radius * math.cos(angle)


FONT, LINE, ICON = 7.5, 8.5, (14.0, 11.0)  # dial text size, line pitch, symbol width and height
GAP = 3.5  # clearance between a label and the ring or a group arc


def text_width(words: str) -> float:
    return len(words) * FONT * 0.56


def label_size(words: str, icon: str | None) -> tuple[float, float]:
    """Width and height of a dial label; a symbol stands beside its text, as on the dial."""
    lines = words.split("\n") if words else []
    widths = [text_width(part) for part in lines] or [0]
    width = max(widths) + (ICON[0] + 1 if icon else 0)
    height = max(LINE * len(lines), ICON[1] if icon else 0)
    return width, height


def reach(physical: int, radius: float, size: tuple[float, float]) -> tuple[float, float]:
    """Nearest and farthest distance from the dial centre of a label placed at `radius`."""
    x, y = polar(radius, physical)
    dx, dy = abs(x - DIAL[0]), abs(y - DIAL[1])
    near = math.hypot(max(dx - size[0] / 2, 0), max(dy - size[1] / 2, 0))
    return near, math.hypot(dx + size[0] / 2, dy + size[1] / 2)


def clear_radius(physical: int, size: tuple[float, float]) -> float:
    """The smallest radius at which a label of that size keeps clear of the detent ring."""
    keep = RING + 2.5 + GAP
    radius = keep
    while reach(physical, radius, size)[0] < keep and radius < keep + 40:
        radius += 0.5
    return radius


def grouped(physical: int) -> bool:
    return any(round(first) <= physical <= round(last) for _, first, last in GROUPS)


def layout() -> tuple[dict[int, float], float]:
    """Radius of every label, and the radius of the group arcs just outside the labels
    they span."""
    radii, outer = {}, ARCS
    for physical, _, words, icon in POSITIONS:
        size = label_size(words, icon)
        radii[physical] = clear_radius(physical, size)
        if grouped(physical):
            outer = max(outer, reach(physical, radii[physical], size)[1] + GAP)
    return radii, outer


def label(words: str, icon: str | None, color: str) -> str:
    lines = words.split("\n") if words else []
    width, _ = label_size(words, icon)
    left = -width / 2
    body = []
    for index, part in enumerate(lines):
        centre = left + max(text_width(p) for p in lines) / 2
        body.append(text(centre, (index - (len(lines) - 1) / 2) * LINE, part, FONT, color))
    if icon:
        x = width / 2 - ICON[0] / 2 if lines else 0
        body.append(f'<g transform="translate({x:.1f},0) scale(0.62)">'
                    + ICONS[icon].format(c=color) + "</g>")
    return "".join(body)


def dial() -> list[str]:
    dash = 2 * math.pi * RING / 24
    parts = [f'<circle cx="{DIAL[0]}" cy="{DIAL[1]}" r="{RING}" fill="none" stroke="{GREEN}"'
             f' stroke-width="5" stroke-dasharray="{dash * 0.72:.2f} {dash * 0.28:.2f}"'
             f' transform="rotate({-90 - 0.36 * STEP:.2f} {DIAL[0]} {DIAL[1]})"/>']
    radii, arcs = layout()
    for physical, value, words, icon in POSITIONS:
        x, y = polar(radii[physical], physical)
        color = DIM if value == 31 else INK
        parts.append(f'<g id="pos-{value}" transform="translate({x:.1f},{y:.1f})">'
                     + label(words, icon, color) + "</g>")
    for name, first, last in GROUPS:
        x1, y1 = polar(arcs, first)
        x2, y2 = polar(arcs, last)
        parts.append(f'<path d="M{x1:.1f},{y1:.1f} A{arcs:.1f},{arcs:.1f} 0 0 1'
                     f' {x2:.1f},{y2:.1f}" fill="none" stroke="{GREEN}" stroke-width="1.2"/>')
        if last > 9:
            x, y = polar(arcs + 12, last + 0.3)
            parts.append(text(x, y - 5, "ZLOOP", 7, GREEN) + text(x, y + 4, "AC/DC", 7, GREEN))
        else:
            x, y = polar(arcs + 4, last + 0.35)
            parts.append(text(x, y, name, 7, GREEN, "start"))
    return parts


def front() -> str:
    body = top() + sockets() + display() + dial()
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
