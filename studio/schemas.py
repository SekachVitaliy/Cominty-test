from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from cominty_sdk import AgentCapabilities
from pydantic import BaseModel

EventKind = Literal["step", "think", "note", "tool"]


@dataclass(frozen=True)
class Tone:
    name: str
    icon: str
    description: str
    instructions: str

    @property
    def label(self) -> str:
        return f":material/{self.icon}: {self.name}"


@dataclass(frozen=True)
class Agent:
    key: str
    title: str
    role: str
    prompt: str
    capabilities: AgentCapabilities
    export_pdf: str | None = None  # file name for the reply exported as PDF

    def render(self, idea: str, tone: Tone, research: str = "") -> str:
        return (
            self.prompt.format(idea=idea, research=research)
            + "\n\nWrite everything in English (text, files, image lettering), even if the"
            + " idea is in another language."
            + f"\n\nTone of voice ({tone.name}). Follow it in every text you write:\n"
            + tone.instructions
        )


@dataclass
class Output:
    name: str
    mimetype: str
    data: bytes

    @property
    def is_image(self) -> bool:
        return self.mimetype.startswith("image/")


# Streamed while an agent works: one row in its activity log.
@dataclass
class AgentEvent:
    agent: str
    key: int  # correlation id: the running and finished phase of a step share it
    status: str
    kind: EventKind
    text: str


# The agent's final answer, or why it failed.
@dataclass
class AgentResult:
    agent: str
    ok: bool
    text: str
    elapsed: float
    outputs: list[Output] = field(default_factory=list[Output])


# What history.py writes to run.json. File bytes live next to it on disk.
class FileRecord(BaseModel):
    name: str
    mimetype: str


class ResultRecord(BaseModel):
    ok: bool
    text: str
    elapsed: float
    files: list[FileRecord]


class RunRecord(BaseModel):
    id: str
    idea: str
    tone: str
    created_at: datetime
    results: dict[str, ResultRecord]

    @property
    def ok(self) -> bool:
        return bool(self.results) and all(r.ok for r in self.results.values())
