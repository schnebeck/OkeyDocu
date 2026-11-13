# OkeyDocu - tests/photo_ui_helpers.py
# Synthetic campaigns and pointer moves for the photo widgets.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime, timedelta

from PIL import Image
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.ui.photo_shared import photo_mime_data, shared_thumbs
from okeydocu.ui.photo_stack import PhotoStack
from okeydocu.ui.photo_timeline import PhotoTimeline

T0 = datetime(2026, 3, 1, 10, 0, 0)
EXIF_IFD = 0x8769
EXIF_DATETIME_ORIGINAL = 36867
LEFT = Qt.MouseButton.LeftButton


def write_photo(path, moment=None, size=(32, 24)):
    image = Image.new("RGB", size, (hash(path.name) % 255, 90, 140))
    exif = image.getexif()
    if moment:
        exif.get_ifd(EXIF_IFD)[EXIF_DATETIME_ORIGINAL] = moment.strftime("%Y:%m:%d %H:%M:%S")
    image.save(path, exif=exif)
    return path


def make_campaign(app, asset, folder, marks=(0, 10, 20), photos=(1, 11)):
    """Measurements and photos at these minutes. Returns (campaign, measurement ids)."""
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    measured = [
        app.service.add_measurement(
            campaign, "rlo", [ResultValue("r", "R", Quantity(raw="0,12 Ω"))],
            T0 + timedelta(minutes=minute), Verdict.PASSED,
        )
        for minute in marks
    ]
    files = [
        write_photo(folder / f"p{minute}.jpg", T0 + timedelta(minutes=minute))
        for minute in photos
    ]
    app.service.import_photos(campaign, files)
    return campaign, measured


def open_timeline(qtbot, app, campaign, size=(860, 190)):
    widget = PhotoTimeline(app)
    qtbot.addWidget(widget)
    widget.resize(*size)
    widget.show()
    qtbot.waitExposed(widget)
    widget.show_campaign(campaign)
    shared_thumbs().finish()
    return widget


def open_stack(qtbot, app, campaign):
    widget = PhotoStack(app)
    qtbot.addWidget(widget)
    widget.resize(320, 260)
    widget.show()
    widget.show_campaign(campaign)
    shared_thumbs().finish()
    return widget


def photo_ids(app, campaign):
    return [row["id"] for row in app.service.photos(campaign)]


def owners(app, campaign):
    return [row["measurement_id"] for row in app.service.photos(campaign)]


def stored_shift(app, campaign):
    return app.service.campaign(campaign)["photo_shift_s"]


def centre_of(view, photo_id) -> QPoint:
    item = view.photo_items[photo_id]
    return item.mapToScene(item.width / 2, item.height / 2).toPoint()


def mark_point(view, mark_id) -> QPoint:
    return QPoint(round(view.axis.x_of(view.data.marks_by_id[mark_id].at)),
                  round(view.tracks.mark_y))


def press(view, pos):
    QTest.mousePress(view.viewport(), LEFT, pos=pos)


def move(view, pos):
    QTest.mouseMove(view.viewport(), pos)


def release(view, pos):
    QTest.mouseRelease(view.viewport(), LEFT, pos=pos)


def click(view, pos):
    QTest.mouseClick(view.viewport(), LEFT, pos=pos)


def drag(view, start, end):
    press(view, start)
    move(view, QPoint((start.x() + end.x()) // 2, (start.y() + end.y()) // 2))
    move(view, end)
    release(view, end)


def carry_over(view, photo_id, pos):
    """A photo carried in from another widget: pass over the view and drop."""
    mime = photo_mime_data(photo_id)
    move_action = Qt.DropAction.MoveAction
    view.dragMoveEvent(QDragMoveEvent(pos, move_action, mime, LEFT, Qt.KeyboardModifier.NoModifier))
    view.dropEvent(
        QDropEvent(QPointF(pos), move_action, mime, LEFT, Qt.KeyboardModifier.NoModifier)
    )


def drop_on(widget, mime, pos=QPoint(10, 10)):
    """Qt hands a drop only to a widget that accepted the drag when it entered."""
    plain = Qt.KeyboardModifier.NoModifier
    enter = QDragEnterEvent(pos, Qt.DropAction.MoveAction, mime, LEFT, plain)
    QApplication.sendEvent(widget, enter)
    event = QDropEvent(QPointF(pos), Qt.DropAction.MoveAction, mime, LEFT, plain)
    QApplication.sendEvent(widget, event)
    return event


def wheel(view, pos, delta, sideways=0):
    view.wheelEvent(QWheelEvent(
        QPointF(pos), QPointF(view.mapToGlobal(pos)), QPoint(), QPoint(sideways, delta),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False,
    ))
