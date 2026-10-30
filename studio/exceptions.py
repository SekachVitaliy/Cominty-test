from __future__ import annotations


class StudioError(Exception):
    """Base for every error the studio raises itself."""


class AgentFailed(StudioError):
    def __init__(self, agent: str, reason: str) -> None:
        super().__init__(f"{agent} stopped: {reason}")
        self.agent = agent
        self.reason = reason


class ToneSkillError(StudioError):
    def __init__(self, path: object, reason: str) -> None:
        super().__init__(f"Bad tone skill {path}: {reason}")
