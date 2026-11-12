# EasyMeasurement - easymeasurement/ui/campaign_items.py
# A campaign as a line of a list: its title, its order, and when with how much.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from ..l10n import moment, plural, tr

SEPARATOR = "  ·  "

def heading(text: str, size: int = 18) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setPointSize(size)
    font.setBold(True)
    label.setFont(font)
    return label


def count_text(count: int) -> str:
    return plural(count, "{count} measurement", "{count} measurements")


def campaign_lines(row, count: int, mark: str = "") -> str:
    """Title, the order and when with how much, a line each; a line with nothing is left out."""
    since = datetime.fromisoformat(row["started_at"])
    details = f"{moment(since)}{SEPARATOR}{count_text(count)}"
    lines = (f"{mark}{row['title']}", order_line(row), details)
    return "\n".join(line for line in lines if line)


def campaign_icon(row) -> QIcon:
    """Open for work, or locked once confirmed."""
    return QIcon.fromTheme("document-edit" if row["status"] == "open" else "object-locked")


def order_line(row) -> str:
    """The job number and the contact person of a campaign, as far as they are given."""
    parts = [tr("Job {number}", number=row["job_number"]) if row["job_number"] else "",
             row["contact"]]
    return SEPARATOR.join(part for part in parts if part)


class CampaignDelegate(QStyledItemDelegate):
    """The title stands out, the lines below it only tell campaigns apart."""

    PADDING = 4

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height() + 2 * self.PADDING)

    def paint(self, painter, option, index) -> None:
        title, *details = (index.data() or "").split("\n")
        if not details:
            super().paint(painter, option, index)
            return
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        item.text = ""
        style = item.widget.style() if item.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, item.widget)
        # Beside the icon, where the style would put a single line of text.
        room = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, item.widget)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        painter.save()
        painter.setPen(option.palette.color(role))
        font = option.font
        line = option.fontMetrics.lineSpacing()
        top = option.rect.top() + self.PADDING
        left, width = room.left() + 4, room.width() - 8
        for number, text in enumerate([title, *details]):
            font.setBold(number == 0)
            painter.setFont(font)
            painter.setOpacity(1.0 if number == 0 or selected else 0.7)
            shown = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, width)
            painter.drawText(QRect(left, top + number * line, width, line),
                             Qt.AlignmentFlag.AlignVCenter, shown)
        painter.restore()
