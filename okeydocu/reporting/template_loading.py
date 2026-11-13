# OkeyDocu - okeydocu/reporting/template_loading.py
# Report templates as text: the shipped ones, read and checked before anything is resolved.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from importlib import resources

import yaml

from ..l10n import N_, tr
from .structure import ORDERS


class TemplateError(Exception):
    """The template is not valid."""


SHIPPED = {"standard.yaml": N_("Standard report"), "compact.yaml": N_("Standard report, compact")}


def shipped_template_text(file: str) -> str:
    return (resources.files("okeydocu") / "data" / "templates" / file).read_text("utf-8")


def default_template_text() -> str:
    return shipped_template_text("standard.yaml")


def parse_template(text: str) -> dict:
    try:
        template = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise TemplateError(tr("The template is not valid YAML: {error}", error=err)) from err
    if not isinstance(template, dict) or not isinstance(template.get("blocks"), list):
        raise TemplateError(tr("The template needs a list “blocks”."))
    _validate(template["blocks"], template.get("images") or {})
    return template


_KNOWN_BLOCKS = {
    "heading", "text", "notice", "fields", "steps", "measurements", "photos", "signature", "logo",
    "attachments", "letterhead", "structure", "summary",
}


def _validate(blocks: list, images: dict, nested: bool = False) -> None:
    for block in blocks:
        kind = block.get("type") if isinstance(block, dict) else None
        if kind not in _KNOWN_BLOCKS:
            raise TemplateError(tr("Unknown block: {kind}", kind=repr(kind)))
        if kind == "steps":
            if nested:
                raise TemplateError(tr("Repetitions cannot be nested."))
            _validate(block.get("blocks", []), images, nested=True)
        if kind == "structure" and nested:
            raise TemplateError(tr("The measurements by structure do not belong in a repetition."))
        if kind == "summary" and nested:
            raise TemplateError(tr("The summary does not belong in a repetition."))
        if kind == "structure" and block.get("order", "place") not in ORDERS:
            raise TemplateError(tr("Unknown order: {order}", order=repr(block.get("order"))))
        if kind == "logo":
            if nested:
                raise TemplateError(tr("A logo does not belong in a repetition."))
            image = block.get("image")
            if image and image not in images:
                raise TemplateError(tr("The image {image} is missing in the template.",
                                       image=repr(image)))
