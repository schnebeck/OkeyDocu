# EasyMeasurement - easymeasurement/campaign/plan.py
# Measurement plans: which steps a campaign has and how each is wired.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib import resources

import yaml


@dataclass(frozen=True)
class Wire:
    socket: str  # instrument socket, e.g. "1(L)"
    target: str  # terminal id on the test object


@dataclass(frozen=True)
class Terminal:
    id: str
    label: str


@dataclass(frozen=True)
class Wiring:
    object_label: str
    terminals: tuple[Terminal, ...]
    wires: tuple[Wire, ...]
    instrument: str = ""
    sockets: tuple[str, ...] = ()


STEP_KINDS = ("measure", "check", "note")


@dataclass(frozen=True)
class PlanStep:
    """One point of a plan: a measurement, a question to answer, or something to read."""

    key: str
    title: str
    kind: str = "measure"
    function: str = ""  # neutral function key
    selector: str = ""  # rotary switch position
    settings: tuple[tuple[str, str], ...] = ()
    wiring: Wiring | None = None
    instructions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    source: str = ""
    also_accepts: tuple[str, ...] = ()
    text: str = ""  # explains a question or holds a note
    expected: str = "yes"  # the answer that counts as passed
    dut: str = ""  # how the test object has to be operated
    # A point of a repeat inspection: where, with which limits and settings, and what
    # the last inspection there left to know. `origin` is "<campaign uuid>/<device uid>".
    asset_id: int | None = None
    limits: tuple[tuple[str, str, str, str], ...] = ()  # key, label, lower, upper
    parameters: tuple[tuple[str, str], ...] = ()
    origin: str = ""
    hint: str = ""
    remark: str = ""
    question: str = ""  # a check asks this; the title is its short name
    run: str = ""  # the run the step belonged to, by name
    run_kind: str = ""

    def accepts(self, function: str) -> bool:
        return function == self.function or function in self.also_accepts

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        wiring = data.get("wiring")
        return cls(
            key=data["key"],
            title=data["title"],
            kind=data.get("kind", "measure"),
            function=data.get("function", ""),
            selector=data.get("selector", ""),
            settings=tuple(tuple(item) for item in data.get("settings", ())),
            wiring=Wiring(
                object_label=wiring["object_label"],
                terminals=tuple(Terminal(**t) for t in wiring["terminals"]),
                wires=tuple(Wire(**w) for w in wiring["wires"]),
                instrument=wiring.get("instrument", ""),
                sockets=tuple(wiring.get("sockets", ())),
            ) if wiring else None,
            instructions=tuple(data.get("instructions", ())),
            warnings=tuple(data.get("warnings", ())),
            source=data.get("source", ""),
            also_accepts=tuple(data.get("also_accepts", ())),
            text=data.get("text", ""),
            expected=data.get("expected", "yes"),
            dut=data.get("dut", ""),
            asset_id=data.get("asset_id"),
            limits=tuple(tuple(item) for item in data.get("limits", ())),
            parameters=tuple(tuple(item) for item in data.get("parameters", ())),
            origin=data.get("origin", ""),
            hint=data.get("hint", ""),
            remark=data.get("remark", ""),
            question=data.get("question", ""),
            run=data.get("run", ""),
            run_kind=data.get("run_kind", ""),
        )


@dataclass(frozen=True)
class Plan:
    key: str
    title: str
    released: bool
    steps: tuple[PlanStep, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        """The name as a campaign states it, which also tells a draft."""
        draft = not self.released and "Entwurf" not in self.title
        return f"{self.title} (Entwurf)" if draft else self.title


def _settings(raw: dict) -> list[tuple[str, str]]:
    return [(k, str(v)) for item in raw.get("settings", ()) for k, v in item.items()]


def _raw_instructions() -> dict[str, dict]:
    folder = resources.files("easymeasurement") / "data" / "instructions"
    found = {}
    for entry in folder.iterdir():
        if entry.name.endswith(".yaml"):
            raw = yaml.safe_load(entry.read_text(encoding="utf-8"))
            found[raw["function"]] = raw
    return found


def load_instructions() -> dict[str, PlanStep]:
    """How each measuring function is set up, by function key."""
    return {
        function: PlanStep.from_dict({**raw, "key": function, "settings": _settings(raw)})
        for function, raw in _raw_instructions().items()
    }


def _parse_step(raw: dict, instructions: dict[str, dict]) -> PlanStep:
    """A measuring step takes what it does not state itself from its function's instruction."""
    data = dict(raw)
    if raw.get("kind", "measure") == "measure":
        data = {**instructions.get(raw.get("function"), {}), **raw}
    data["settings"] = _settings(data)
    data.setdefault("title", data["key"])
    return PlanStep.from_dict(data)


def parse_plan(text: str) -> Plan:
    raw = yaml.safe_load(text)
    instructions = _raw_instructions()
    return Plan(
        key=raw["key"],
        title=raw["title"],
        released=bool(raw.get("released", False)),
        steps=tuple(_parse_step(step, instructions) for step in raw.get("steps") or ()),
    )


def builtin_plan_texts() -> list[str]:
    folder = resources.files("easymeasurement") / "data" / "plans"
    return [
        entry.read_text(encoding="utf-8")
        for entry in sorted(folder.iterdir(), key=lambda e: e.name)
        if entry.name.endswith(".yaml")
    ]


def load_plans() -> list[Plan]:
    return [parse_plan(text) for text in builtin_plan_texts()]
