# OkeyDocu - okeydocu/ui/templates.py
# Graphical template editor: blocks, their properties and a live preview for 0, 1 and n.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QBuffer, Qt, QTimer
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from ..l10n import current, plural, tr
from ..reporting.language import languages
from ..reporting.template_model import BLOCK_LABELS
from .board import GutterSplitter
from .common import AppContext
from .template_blocks import TemplateBlocks
from .template_data_forms import TemplateDataForms
from .template_structure_form import TemplateStructureForm
from .template_document import TemplateDocument
from .template_forms import TemplateForms
from .template_logo_form import TemplateLogoForm

_PREVIEW_DELAY_MS = 350


class TemplatesPage(
    TemplateDocument, TemplateBlocks, TemplateForms, TemplateDataForms, TemplateStructureForm,
    TemplateLogoForm, QWidget
):
    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.template: dict = {"blocks": []}
        self.dirty = False
        self._loading = False
        self._debounce = QTimer(self, singleShot=True, interval=_PREVIEW_DELAY_MS)
        self._debounce.timeout.connect(self.preview)

        self.choice = QComboBox()
        self.choice.currentIndexChanged.connect(self._chosen)
        self._shown_index = -1
        save = QPushButton(tr("Save"))
        copy_button = QPushButton(tr("As new template"))
        self.delete_button = QPushButton(tr("Delete template"))
        save.clicked.connect(self._save)
        copy_button.clicked.connect(self._save_as)
        self.delete_button.clicked.connect(self._delete)
        self.count = QComboBox()
        for shown in (0, 1, 4):
            self.count.addItem(plural(shown, "Preview: {count} measurement",
                                      "Preview: {count} measurements"), shown)
        self.count.setCurrentIndex(2)
        self.count.currentIndexChanged.connect(self.preview)
        self.preview_language = QComboBox()
        for code, name in languages().items():
            self.preview_language.addItem(name, code)
        self.preview_language.setCurrentIndex(max(0, self.preview_language.findData(current())))
        self.preview_language.setToolTip(tr("The preview shows the report in this language"))
        self.preview_language.currentIndexChanged.connect(self.preview)
        self.state = QLabel()
        bar = QHBoxLayout()
        for widget in (self.choice, save, copy_button, self.delete_button, self.state):
            bar.addWidget(widget)
        bar.addStretch()
        bar.addWidget(self.preview_language)
        bar.addWidget(self.count)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #b03a2e")

        # Block list
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.currentItemChanged.connect(lambda *_: self._show_form())
        menu = QMenu(self)
        for kind, label in BLOCK_LABELS.items():
            menu.addAction(tr(label), lambda kind=kind: self.add_block(kind))
        self.add_button = QToolButton()
        self.add_button.setText(tr("Add block"))
        self.add_button.setMenu(menu)
        self.add_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.up_button = QPushButton("↑")
        self.down_button = QPushButton("↓")
        self.into_button = QPushButton(tr("→ into repeat"))
        self.out_button = QPushButton(tr("← out"))
        self.remove_button = QPushButton(tr("Remove"))
        self.up_button.setToolTip(tr("Up (Alt+↑)"))
        self.down_button.setToolTip(tr("Down (Alt+↓)"))
        self.up_button.clicked.connect(lambda: self.move_block(-1))
        self.down_button.clicked.connect(lambda: self.move_block(1))
        self.into_button.clicked.connect(self.move_into)
        self.out_button.clicked.connect(self.move_out)
        self.remove_button.clicked.connect(self.remove_block)
        QShortcut(QKeySequence("Alt+Up"), self.tree, lambda: self.move_block(-1))
        QShortcut(QKeySequence("Alt+Down"), self.tree, lambda: self.move_block(1))
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tree, self.remove_block)
        buttons = QHBoxLayout()
        for widget in (self.add_button, self.up_button, self.down_button, self.into_button,
                       self.out_button, self.remove_button):
            buttons.addWidget(widget)
        buttons.addStretch()

        self.form_host = QScrollArea()
        self.form_host.setWidgetResizable(True)

        structure = QSplitter(Qt.Orientation.Vertical, objectName="template-structure")
        structure.addWidget(self.tree)
        structure.addWidget(self.form_host)
        structure.setStretchFactor(0, 1)
        structure.setStretchFactor(1, 2)
        structure.setSizes([280, 460])
        visual = QWidget()
        visual_layout = QVBoxLayout(visual)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        visual_layout.addLayout(buttons)
        visual_layout.addWidget(structure, 1)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.textChanged.connect(self._source_edited)
        self.modes = QTabWidget()
        self.modes.addTab(visual, tr("Layout"))
        self.modes.addTab(self.editor, tr("Source"))
        self.modes.currentChanged.connect(self._mode_changed)
        self.visual = visual

        self.document = QPdfDocument(self)
        self.view = QPdfView()
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._buffer: QBuffer | None = None

        splitter = GutterSplitter(objectName="template-editor")
        splitter.addWidget(self.modes)
        splitter.addWidget(self.view)
        splitter.setSizes([640, 700])
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.message)
        layout.addWidget(splitter, 1)
        self.reload()
