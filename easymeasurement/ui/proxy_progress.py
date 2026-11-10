# EasyMeasurement - easymeasurement/ui/proxy_progress.py
# Follows the reduced copies of photos being made in the background, campaign by campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from concurrent.futures import Future

from PySide6.QtCore import QObject, QTimer, Signal

POLL_MS = 250


class ProxyProgress(QObject):
    """Asks the workers' futures on a timer, so no signal has to cross from their threads."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pending: dict[int, list[Future]] = {}
        self._timer = QTimer(self, interval=POLL_MS)
        self._timer.timeout.connect(self._poll)

    def follow(self, campaign_id: int, futures: list[Future]) -> None:
        if not futures:
            return
        self.pending[campaign_id] = [*self.pending.get(campaign_id, []), *futures]
        self._timer.start()
        self.changed.emit()

    def ready(self, campaign_id: int | None) -> bool:
        return all(future.done() for future in self.pending.get(campaign_id, []))

    def counts(self) -> tuple[int, int]:
        futures = [future for group in self.pending.values() for future in group]
        return sum(future.done() for future in futures), len(futures)

    def text(self) -> str:
        done, total = self.counts()
        return f"Bereite Fotos für das Protokoll vor: {done} von {total}" if done < total else ""

    def _poll(self) -> None:
        for campaign_id in [key for key in self.pending if self.ready(key)]:
            del self.pending[campaign_id]
        if not self.pending:
            self._timer.stop()
        self.changed.emit()
