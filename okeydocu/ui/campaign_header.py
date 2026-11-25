# OkeyDocu - okeydocu/ui/campaign_header.py
# The head of the campaign workspace: which campaign, what can be done and what is left.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The head is one block of two parts. Left stands what the campaign is: its title and, a line
each, whom it is for, what is tested, who tests and by which plan. Right stands what can be
done with it, and below that what is left before it can be ended."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QToolButton, QWidget

from ..l10n import N_, tr
from .board import UNIT
from .campaign_items import heading
from .dashboard_card import dim_colour
from .elided_label import ElidedLabel
from .framed import TEXT, Framed
from .wrapping_label import WrappingLabel

LINE = ('<tr><td style="color:{dim}; padding-right:{gap}px;">{name}</td>'
        '<td>{text}</td></tr>')
NAME_GAP = 4 * UNIT  # between the names of the lines and what they say
LISTED = 8  # blockers the tool tip of the ending button names before it trails off
END_TIP = N_("Ends and seals the campaign and files the report, signed if wanted. Nothing can be"
             " changed afterwards.")


class CampaignHeader(Framed):
    """Says which campaign this is and offers what can be done with it now."""

    tester_requested = Signal()
    edit_requested = Signal()
    home_requested = Signal()
    check_requested = Signal(str)  # a link in the checks: what to look at

    def __init__(self):
        super().__init__(joined=True)
        self.home_button = QToolButton()
        self.home_button.setIcon(QIcon.fromTheme(
            "go-home", self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon)))
        self.home_button.setToolTip(tr("To the overview (Alt+Home)"))
        self.home_button.setAutoRaise(True)
        self.home_button.clicked.connect(self.home_requested)
        self.title = heading("", 15, ElidedLabel)
        self.edit_button = QToolButton()
        fallback = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.edit_button.setIcon(QIcon.fromTheme("document-edit", fallback))
        self.edit_button.setAccessibleName(tr("Edit campaign"))
        self.edit_button.setToolTip(tr("Change title, installation and contact person"))
        self.edit_button.setAutoRaise(True)
        self.edit_button.clicked.connect(self.edit_requested)
        self.details = WrappingLabel()
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.linkActivated.connect(lambda _: self.tester_requested.emit())
        self.resume_button = QPushButton(tr("Resume measuring"))
        self.pause_button = QPushButton(tr("Pause measuring"))
        self.photos_button = QPushButton(tr("Photos …"))
        self.photos_button.setToolTip(tr("Import photos; they are assigned by the time they"
                                         " were taken."))
        self.assign_button = QPushButton(tr("Assign photos"), checkable=True)
        self.assign_button.setToolTip(tr("Show or hide the photo timeline below the table (F7)."))
        self.draft_button = QPushButton(tr("Report preview"))
        self.draft_button.setToolTip(tr("The report as it would look now. It is not valid yet."))
        self.finish_button = QPushButton(QIcon.fromTheme("object-locked"), tr("End campaign …"))
        self.finish_button.setToolTip(tr(END_TIP))
        # What is left before confirming, with links to the rows concerned.
        self.checks = QLabel()
        self.checks.setTextFormat(Qt.TextFormat.RichText)
        self.checks.linkActivated.connect(self.check_requested)
        self.report_button = QPushButton(tr("Create report …"))
        self.delete_button = QPushButton(QIcon.fromTheme("edit-delete"), tr("Delete"))
        self.delete_button.setToolTip(tr("Nothing has been recorded yet. An empty campaign is"
                                         " deleted, not ended."))
        self.buttons = (self.resume_button, self.pause_button, self.photos_button,
                        self.assign_button, self.draft_button, self.finish_button,
                        self.delete_button, self.report_button)
        self.actions = QWidget()
        row = QHBoxLayout(self.actions)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2 * UNIT)
        for button in self.buttons:
            row.addWidget(button)
            # Shown by the campaign that needs them; hidden pages keep their first layout.
            button.hide()
        top = QHBoxLayout()
        top.setSpacing(UNIT)
        top.addWidget(self.home_button)
        top.addWidget(self.title)
        top.addWidget(self.edit_button)
        top.addStretch(1)
        top.addSpacing(2 * UNIT)
        top.addWidget(self.actions)
        about = QHBoxLayout()
        about.setContentsMargins(TEXT, 0, TEXT, 0)
        about.setSpacing(4 * UNIT)
        about.addWidget(self.details, 1, Qt.AlignmentFlag.AlignTop)
        about.addWidget(self.checks, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.box.addLayout(top)
        self.box.addLayout(about)

    def show_details(self, lines) -> None:
        """`lines` are pairs of a name and what it stands for, as rich text. Each gets a line
        of its own, the names dimmed in one column."""
        dim = dim_colour(self.palette()).name()
        rows = (LINE.format(dim=dim, gap=NAME_GAP, name=name, text=text) for name, text in lines)
        self.details.setText(f'<table cellspacing="0" cellpadding="0">{"".join(rows)}</table>')

    def show_blockers(self, blockers: list[str]) -> None:
        """The campaign cannot be ended while something stands in the way; the button says
        what."""
        self.finish_button.setEnabled(not blockers)
        told = blockers[:LISTED] + (["…"] if len(blockers) > LISTED else [])
        waiting = "\n".join([tr("Not possible yet:"), *told])
        self.finish_button.setToolTip(waiting if blockers else tr(END_TIP))

    def span(self, count: int | None = None) -> int | None:
        """The width of the last `count` actions on show with the room between them, of all
        without a count. None if there are fewer."""
        shown = [button for button in self.buttons if not button.isHidden()]
        taken = shown if count is None else shown[-count:]
        if not taken or (count is not None and len(shown) < count):
            return None
        return sum(button.sizeHint().width() for button in taken) + 2 * UNIT * (len(taken) - 1)
