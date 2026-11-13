# OkeyDocu - okeydocu/reporting/template.py
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

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from ..vocabulary import function_markup
from .context import ReportMeasurement
from ..l10n import N_, tr
from .language import pick
from .logo import LogoError, decode_logo
from .footnotes import Footnotes
from .measurement_views import group_nodes, place_nodes, remaining_photos, scope, single
from .structure import structure_nodes
from .summary import SummaryPlace, summary_nodes
from .template_loading import (  # noqa: F401
    SHIPPED,
    TemplateError,
    default_template_text,
    parse_template,
    shipped_template_text,
)
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
    # A summary speaks of the whole report, so it is filled in once the rest is known.
    nodes = [part for node in nodes
             for part in (summary_nodes(values) if isinstance(node, SummaryPlace) else [node])]
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
        elif kind == "summary":
            nodes.append(SummaryPlace(block))
        elif kind == "photos":
            items = remaining_photos(scope(values), values["_footnotes"])
            if items:
                nodes.append(Photos(items))
        elif kind == "attachments":
            nodes.extend(place_nodes(values.get("places", [])))
        elif kind == "signature":
            nodes.append(SignatureLine(
                [_render(label, values) for label in block.get("labels", ["Place, date", "Inspector"])],
                # A draft is no valid report, so it carries no signature.
                None if values["campaign"].get("draft") else values["campaign"].get("signature"),
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
