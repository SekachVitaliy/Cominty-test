from __future__ import annotations

from pathlib import Path

from studio.config import settings
from studio.exceptions import ToneSkillError
from studio.schemas import Tone


# A tone skill is a Markdown file: a `key: value` header between `---` lines, then
# the instructions every agent follows. Drop a new file into skills/ to add a tone.
def load_tones(folder: Path = settings.skills_dir) -> list[Tone]:
    tones = []
    for path in sorted(folder.glob("*.md")):
        try:
            _, header, body = path.read_text(encoding="utf-8").split("---", 2)
            meta = dict(line.split(":", 1) for line in header.strip().splitlines())
            tones.append(
                Tone(**{k.strip(): v.strip() for k, v in meta.items()}, instructions=body.strip())
            )
        except (ValueError, TypeError) as exc:
            raise ToneSkillError(path, "expected a ---name/icon/description--- header") from exc
    return tones
