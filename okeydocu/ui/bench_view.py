# OkeyDocu - okeydocu/ui/bench_view.py
# The bench of a guided measurement: front panel above, test point below, test leads between.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The leads are laid one after the other in the order the guide places the probes, each
plug's row pulsing while its lead is laid. The leads are painted by a transparent layer above
panel and test point, so they can run across both."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..devices.guide import Guide
from ..l10n import tr
from .front_panel import FrontPanel
from .lead_art import paint_lead, route
from .test_objects import DRAWINGS

LAY_MS = 900  # one lead
PANEL_SHARE = 0.64  # of the height, at most
LANE_GAP = 28  # between two lanes beside the socket field
PLUG = (124, 40)  # plug size in panel units, over all three sockets of a row


class _Leads(QWidget):
    def __init__(self, bench: "BenchView"):
        super().__init__(bench)
        self.bench = bench
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bench.paint_leads(painter)


class BenchView(QWidget):
    def __init__(self, drawing, parent=None):
        super().__init__(parent)
        self.panel = FrontPanel(drawing, self)
        self.leads_layer = _Leads(self)
        self.guide: Guide | None = None
        self.data: list[str] = []
        self.poles = 2
        self.n_left = False
        self.anchors: dict = {}
        self.progress = 0.0
        self._lay = QVariantAnimation(self, startValue=0.0)
        self._lay.setEasingCurve(QEasingCurve.Type.Linear)
        self._lay.valueChanged.connect(self._laid)
        self.setMinimumSize(640, 520)

    def show_guide(self, guide: Guide, data: list[str], poles: int = 2,
                   n_left: bool = False) -> None:
        """`data` is what the test point states of itself, such as rated residual current
        and type of an RCD; `poles` and `n_left` how its terminals are laid out."""
        self.guide, self.data, self.poles, self.n_left = guide, data, poles, n_left
        self.panel.turn_to(guide.selector)
        self.progress = 0.0
        self.update()

    def lay_leads(self) -> None:
        if self.guide is None:
            return
        count = len(self.guide.leads)
        self._lay.stop()
        self._lay.setStartValue(0.0)
        self._lay.setEndValue(float(count))
        self._lay.setDuration(LAY_MS * count)
        self._lay.start()

    def finish(self) -> None:
        """Every lead laid at once, for a tester who goes on without watching."""
        self._lay.stop()
        self._laid(float(len(self.guide.leads)) if self.guide else 0.0)

    def _laid(self, value) -> None:
        self.progress = float(value)
        if self.guide is not None:
            started = [lead.row for lead in self.guide.leads[:int(self.progress) + 1]]
            self.panel.point_at(*started)
        self.update()
        self.leads_layer.update()

    # Layout and painting --------------------------------------------------------

    def resizeEvent(self, _event) -> None:
        height = min(int(self.width() * 725 / 1040), int(self.height() * PANEL_SHARE))
        self.panel.setGeometry(0, 0, self.width(), height)
        self.leads_layer.setGeometry(self.rect())
        self.leads_layer.raise_()

    def object_box(self) -> QRectF:
        top = self.panel.height() + 20
        return QRectF(self.width() * 0.04, top, self.width() * 0.92, self.height() - top - 6)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = self.object_box()
        painter.setPen(QPen(QColor("#9aa5ae"), 1.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(box, 10, 10)
        if self.guide is None:
            return
        draw = DRAWINGS[self.guide.test_object]
        self.anchors = draw(painter, box, self.data, self.poles, self.n_left)
        painter.setPen(QColor("#1f2933"))
        painter.drawText(box.adjusted(box.width() * 0.72, 16, -12, 0),
                         Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                         tr(self.guide.test_point))

    def paint_leads(self, painter: QPainter) -> None:
        if self.guide is None or not self.anchors:
            return
        scale = self.panel._frame()[0]
        field = self.panel.part_rect("socket-1").left()
        rows = sorted({lead.row for lead in self.guide.leads})
        # Leads reaching their terminal from below turn the deeper the further right it is,
        # so a lead passing beneath another probe never crosses that probe's lead.
        below = sorted((lead for lead in self.guide.leads
                        if self.anchors[lead.terminal].side > 0),
                       key=lambda lead: self.anchors[lead.terminal].point.x())
        for index, lead in enumerate(self.guide.leads):
            anchor = self.anchors[lead.terminal]
            row = self.panel.part_rect(lead.row)
            plug = QRectF(row.left() - 4 * scale, row.top() - 3 * scale,
                          PLUG[0] * scale, PLUG[1] * scale)
            lane = field - LANE_GAP * (len(rows) - rows.index(lead.row))
            depth = 18 + 16 * below.index(lead) if lead in below else 34
            path = route(QPointF(plug.left(), plug.center().y()), lane, anchor, depth)
            left = anchor.side > 0 and lead is below[0]
            paint_lead(painter, plug, lead.plug, path, anchor, lead.probe, left,
                       self.progress - index)
