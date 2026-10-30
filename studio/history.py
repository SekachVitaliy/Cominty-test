from __future__ import annotations

from datetime import datetime
from pathlib import Path

from studio.config import settings
from studio.schemas import AgentResult, FileRecord, Output, ResultRecord, RunRecord


# A run is a folder: run.json with the texts, plus every generated file under <agent>/.
def save_run(
    idea: str, tone: str, results: dict[str, AgentResult], root: Path = settings.runs_dir
) -> str:
    created = datetime.now()
    run = RunRecord(
        id=created.strftime("%Y%m%d-%H%M%S"), idea=idea, tone=tone, created_at=created, results={}
    )
    folder = root / run.id
    for key, result in results.items():
        files = []
        for out in result.outputs:
            name = Path(out.name).name  # agent-chosen name: never let it leave the folder
            path = folder / key / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(out.data)
            files.append(FileRecord(name=name, mimetype=out.mimetype))
        run.results[key] = ResultRecord(
            ok=result.ok, text=result.text, elapsed=result.elapsed, files=files
        )
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "run.json").write_text(run.model_dump_json(indent=2))
    return run.id


def list_runs(root: Path = settings.runs_dir) -> list[RunRecord]:
    paths = sorted(root.glob("*/run.json"), reverse=True)
    return [RunRecord.model_validate_json(p.read_text()) for p in paths]


def load_run(
    run_id: str, root: Path = settings.runs_dir
) -> tuple[RunRecord, dict[str, AgentResult]]:
    folder = root / Path(run_id).name
    run = RunRecord.model_validate_json((folder / "run.json").read_text())
    results = {
        key: AgentResult(
            key,
            r.ok,
            r.text,
            r.elapsed,
            [Output(f.name, f.mimetype, (folder / key / f.name).read_bytes()) for f in r.files],
        )
        for key, r in run.results.items()
    }
    return run, results


if __name__ == "__main__":
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    result = AgentResult("pm", True, "hi", 3.0, [Output("../../evil.txt", "text/plain", b"x")])
    run_id = save_run("idea", "Bold", {"pm": result}, tmp)
    assert (tmp / run_id / "pm" / "evil.txt").read_bytes() == b"x"
    run, results = load_run(run_id, tmp)
    assert results["pm"].text == "hi" and results["pm"].outputs[0].data == b"x"
    assert results["pm"].elapsed == 3.0 and run.ok and list_runs(tmp)[0].idea == "idea"
    print("ok")
