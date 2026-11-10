# EasyMeasurement - easymeasurement/reporting/template.py
# Report templates: blocks that resolve to document nodes, handling 0, 1 or n measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A template is a list of blocks. A measurement block does not assume how many
measurements a data set holds. It declares three presentations and the data
picks one:

    none  no measurement: a sentence, or nothing at all
    one   a single measurement: label/value fields, reads like a form
    many  several measurements: a table with a summary row

Measurements of different functions never share a table, because their columns
differ; each function in a step is counted and presented on its own.
"""
from __future__ import annotations

from importlib import resources

import jinja2
import yaml
from jinja2.sandbox import SandboxedEnvironment

from .context import ReportMeasurement, function_label
from .language import pick, tr
from .logo import LogoError, decode_logo
from .measurement_views import (  # noqa: F401
    _many,
    _marks,
    _scope,
    _single,
    _step_photos,
    place_nodes,
)
from .nodes import (  # noqa: F401
    Fields,
    Heading,
    Letterhead,
    Logo,
    Node,
    Notice,
    Paragraph,
    Photos,
    SignatureLine,
    Table,
)

DRAFT_NOTICE = "ENTWURF – die Kampagne ist noch offen, dieses Protokoll ist nicht gültig."
SIMULATED_NOTICE = "SIMULIERTE MESSWERTE – kein gültiges Prüfprotokoll."
_env = SandboxedEnvironment(undefined=jinja2.ChainableUndefined, autoescape=False)


class TemplateError(Exception):
    """The template is not valid."""


# Loading ----------------------------------------------------------------


def default_template_text() -> str:
    source = resources.files("easymeasurement") / "data" / "templates" / "standard.yaml"
    return source.read_text(encoding="utf-8")


def parse_template(text: str) -> dict:
    try:
        template = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise TemplateError(f"Die Vorlage ist kein gültiges YAML: {err}") from err
    if not isinstance(template, dict) or not isinstance(template.get("blocks"), list):
        raise TemplateError("Die Vorlage braucht eine Liste „blocks“.")
    _validate(template["blocks"], template.get("images") or {})
    return template


_KNOWN_BLOCKS = {
    "heading", "text", "notice", "fields", "steps", "measurements", "photos", "signature", "logo",
    "attachments", "letterhead",
}


def _validate(blocks: list, images: dict, nested: bool = False) -> None:
    for block in blocks:
        kind = block.get("type") if isinstance(block, dict) else None
        if kind not in _KNOWN_BLOCKS:
            raise TemplateError(f"Unbekannter Block: {kind!r}")
        if kind == "steps":
            if nested:
                raise TemplateError("Wiederholungen lassen sich nicht verschachteln.")
            _validate(block.get("blocks", []), images, nested=True)
        if kind == "logo":
            if nested:
                raise TemplateError("Ein Logo gehört nicht in eine Wiederholung.")
            image = block.get("image")
            if image and image not in images:
                raise TemplateError(f"Das Bild {image!r} fehlt in der Vorlage.")


# Resolving --------------------------------------------------------------


def _render(text: str, values: dict) -> str:
    try:
        return _env.from_string(pick(text)).render(**values)
    except jinja2.TemplateError as err:
        raise TemplateError(f"Fehler im Platzhalter {text!r}: {err}") from err


def _applies(block: dict, values: dict) -> bool:
    condition = block.get("when")
    if condition is None:
        return True
    return _render("{{ 1 if (" + str(condition) + ") else '' }}", values) != ""


def resolve(template: dict, context: dict) -> list[Node]:
    """Warnings stand first, or right below a letterhead that opens the report."""
    warnings: list[Node] = []
    if context["campaign"].get("draft"):
        warnings.append(Notice(tr(DRAFT_NOTICE)))
    if context["campaign"].get("simulated"):
        warnings.append(Notice(tr(SIMULATED_NOTICE)))
    nodes: list[Node] = []
    _resolve_blocks(template["blocks"], {**context, "_images": template.get("images") or {}}, nodes)
    head = 0
    for index, node in enumerate(nodes):  # logos stand apart from the flow of the text
        if isinstance(node, Letterhead):
            head = index + 1
        if not isinstance(node, Logo):
            break
    return nodes[:head] + warnings + nodes[head:]


def _resolve_blocks(blocks: list[dict], values: dict, nodes: list[Node]) -> None:
    for block in blocks:
        if not _applies(block, values):
            continue
        kind = block["type"]
        if kind == "heading":
            nodes.append(Heading(_render(block["text"], values), int(block.get("level", 1))))
        elif kind == "text":
            nodes.append(Paragraph(_render(block["text"], values)))
        elif kind == "notice":
            nodes.append(Notice(_render(block["text"], values)))
        elif kind == "fields":
            rows = [(_render(label, values), _render(value, values))
                    for label, value in block.get("rows", [])]
            if block.get("features"):  # what is noted on the asset or another element
                rows += list(values.get(block["features"], {}).get("features", []))
            nodes.append(Fields(rows))
        elif kind == "steps":
            for step in values["steps"]:
                _resolve_blocks(block.get("blocks", []), {**values, "step": step}, nodes)
        elif kind == "measurements":
            nodes.extend(_resolve_measurements(block, values))
        elif kind == "photos":
            items = _step_photos(_scope(values))
            if items:
                nodes.append(Photos(items))
        elif kind == "attachments":
            nodes.extend(place_nodes(values.get("places", [])))
        elif kind == "signature":
            nodes.append(SignatureLine(
                [_render(label, values) for label in block.get("labels", ["Ort, Datum", "Prüfer"])],
                values.get("campaign", {}).get("signature"),
                _render(block.get("result", ""), values), values.get("verdict_tone", ""),
            ))
        elif kind == "letterhead":
            nodes.append(Letterhead(
                _render(block.get("title", ""), values), *(
                    [line for line in (_render(text, values).strip() for text in block.get(key, []))
                     if line] for key in ("lines", "client", "contractor")),
                values["campaign"].get("uuid", "") if block.get("qr", True) else "",
                values.get("company_logo") if block.get("logo", True) else None,
            ))
        elif kind == "logo" and block.get("image"):
            try:
                data = decode_logo(values["_images"][block["image"]])
            except LogoError as err:
                raise TemplateError(str(err)) from err
            nodes.append(
                Logo(
                    data, float(block.get("x_mm", 0)), float(block.get("y_mm", 0)),
                    float(block.get("width_mm", 40)), block.get("pages") == "all",
                    bool(block.get("reserve", True)),
                )
            )


def _resolve_measurements(block: dict, values: dict) -> list[Node]:
    step = _scope(values)
    wanted = block.get("function", "*")
    selected = [m for m in step.measurements if wanted in ("*", m.data.function)]
    if not selected:
        none = block.get("none", {})
        if none.get("hide"):
            return []
        return [Paragraph(_render(none.get("text", "Keine Messung."), values))]

    groups: dict[str, list[ReportMeasurement]] = {}
    for measurement in selected:
        groups.setdefault(measurement.data.function, []).append(measurement)

    nodes: list[Node] = []
    for function, group in groups.items():
        if len(groups) > 1:
            nodes.append(Heading(function_label(function), 3))
        if len(group) == 1:
            nodes.append(_single(group[0], block.get("one", {})))
        else:
            nodes.extend(_many(group, block.get("many", {})))
    return nodes
