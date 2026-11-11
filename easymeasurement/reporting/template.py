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

import re

from importlib import resources

import jinja2
import yaml
from jinja2.sandbox import SandboxedEnvironment

from ..vocabulary import function_markup
from .context import ReportMeasurement
from ..l10n import N_, tr
from .language import pick
from .logo import LogoError, decode_logo
from .footnotes import Footnotes
from .measurement_views import group_nodes, place_nodes, remaining_photos, scope, single
from .structure import ORDERS, structure_nodes
from .nodes import (  # noqa: F401
    Fields,
    Heading,
    Letterhead,
    Logo,
    Markup,
    Node,
    Notice,
    Paragraph,
    Photos,
    SignatureLine,
    Table,
)

DRAFT_NOTICE = N_("DRAFT – the inspection is still open, this report is not valid.")
SIMULATED_NOTICE = N_("SIMULATED VALUES – not a valid test report.")
_env = SandboxedEnvironment(undefined=jinja2.ChainableUndefined, autoescape=False)
# Headings may hold symbols set as in mathematics: their data is escaped, markup kept.
_marked = SandboxedEnvironment(undefined=jinja2.ChainableUndefined, autoescape=True)


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
        raise TemplateError(tr("The template is not valid YAML: {error}", error=err)) from err
    if not isinstance(template, dict) or not isinstance(template.get("blocks"), list):
        raise TemplateError(tr("The template needs a list “blocks”."))
    _validate(template["blocks"], template.get("images") or {})
    return template


_KNOWN_BLOCKS = {
    "heading", "text", "notice", "fields", "steps", "measurements", "photos", "signature", "logo",
    "attachments", "letterhead", "structure",
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
        if kind == "structure" and block.get("order", "place") not in ORDERS:
            raise TemplateError(tr("Unknown order: {order}", order=repr(block.get("order"))))
        if kind == "logo":
            if nested:
                raise TemplateError(tr("A logo does not belong in a repetition."))
            image = block.get("image")
            if image and image not in images:
                raise TemplateError(tr("The image {image} is missing in the template.",
                                       image=repr(image)))


# Resolving --------------------------------------------------------------


def _render(text: str, values: dict, env=_env) -> str:
    try:
        return env.from_string(pick(text)).render(**values)
    except jinja2.TemplateError as err:
        message = tr("Error in the placeholder {text}: {error}", text=repr(text), error=err)
        raise TemplateError(message) from err


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
    values = {**context, "_images": template.get("images") or {}, "_footnotes": Footnotes()}
    _resolve_blocks(template["blocks"], values, nodes)
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
            text = Markup(_render(block["text"], values, _marked))
            nodes.append(Heading(text, int(block.get("level", 1))))
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
        elif kind == "structure":
            nodes.extend(structure_nodes(block, values))
        elif kind == "photos":
            items = remaining_photos(scope(values), values["_footnotes"])
            if items:
                nodes.append(Photos(items))
        elif kind == "attachments":
            nodes.extend(place_nodes(values.get("places", [])))
        elif kind == "signature":
            nodes.append(SignatureLine(
                [_render(label, values) for label in block.get("labels", ["Place, date", "Inspector"])],
                values.get("campaign", {}).get("signature"),
                _render(block.get("result", ""), values), values.get("verdict_tone", ""),
                [_render(text, values).strip() for text in block.get("fills", [])],
            ))
        elif kind == "letterhead":
            nodes.append(Letterhead(
                _render(block.get("title", ""), values),
                *(_lines(block.get(key, []), values) for key in ("lines", "client", "contractor")),
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


_FIELD = re.compile(r"{{(.*?)}}")


def _lines(texts: list[str], values: dict) -> list[str]:
    """Lines of a letterhead. One whose data fields are all empty is left out, so a label
    such as "Phone:" never stands alone."""
    kept = []
    for text in texts:
        fields = _FIELD.findall(pick(text))
        if fields and not any(_render("{{" + field + "}}", values).strip() for field in fields):
            continue
        line = _render(text, values).strip()
        if line:
            kept.append(line)
    return kept


def _resolve_measurements(block: dict, values: dict) -> list[Node]:
    step = scope(values)
    wanted = block.get("function", "*")
    selected = [m for m in step.measurements if wanted in ("*", m.data.function)]
    if not selected:
        none = block.get("none", {})
        if none.get("hide"):
            return []
        return [Paragraph(_render(none.get("text", "No measurement."), values))]

    groups: dict[str, list[ReportMeasurement]] = {}
    for measurement in selected:
        groups.setdefault(measurement.data.function, []).append(measurement)

    nodes: list[Node] = []
    notes = values["_footnotes"]
    for function, group in groups.items():
        if len(groups) > 1:
            nodes.append(Heading(Markup(function_markup(function)), 3))
        if len(group) == 1:
            nodes.append(single(group[0], block.get("one", {}), notes))
        else:
            nodes.extend(group_nodes(group, block.get("many", {}), notes))
    return nodes
