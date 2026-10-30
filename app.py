from __future__ import annotations

import asyncio
import html
from pathlib import Path

import streamlit as st

from studio.agents import AGENTS, RESEARCHER
from studio.history import list_runs, load_run, save_run
from studio.pipeline import brand_name, run_studio
from studio.schemas import AgentEvent, AgentResult, Output
from studio.tones import load_tones

EXAMPLES = [
    "A service that matches dog owners for shared walks",
    "AI tutor that teaches kids chess through bedtime stories",
    "Marketplace for renting camping gear from your neighbours",
]
STEPS = ["Research", "Design, backlog and deck", "Startup kit ready"]

# Lucide icons (lucide.dev), one stroke family for every agent.
_SVG = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
    'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
)
ICONS = {
    "researcher": _SVG.format('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
    "designer": _SVG.format(
        '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/>'
        '<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'
    ),
    "pm": _SVG.format(
        '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/>'
        '<path d="M13 12h8"/><path d="M13 18h8"/>'
    ),
    "writer": _SVG.format(
        '<path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/>'
        '<path d="m7 21 5-5 5 5"/>'
    ),
}


@st.cache_data
def css() -> str:
    return Path(__file__).with_name("assets").joinpath("style.css").read_text()


st.set_page_config(page_title="Startup Studio", page_icon=":material/rocket_launch:", layout="wide")
st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)
st.markdown(
    """<div class="hero"><h1>Startup Studio</h1>
    <p>One sentence in. Four Cominty managed agents research the market, design the logo,
    plan the MVP backlog and build the pitch deck while you watch.</p></div>""",
    unsafe_allow_html=True,
)

# Results live in session_state: widget clicks rerun the script, and the run must not repeat.
state = st.session_state
state.setdefault("results", {})
state.setdefault("idea", "")
state.setdefault("run_tone", "")


def open_run(run_id: str) -> None:
    # Callbacks run before the script, so the rerun below already sees the loaded run.
    run, state.results = load_run(run_id)
    state.idea, state.run_tone = run.idea, run.tone


left, mid, right = st.columns([8, 2, 1], vertical_alignment="bottom")
left.text_input("Startup idea", key="idea", placeholder="Describe your startup in one sentence")
launched = mid.button(
    "Launch team", icon=":material/rocket_launch:", type="primary", width="stretch"
)
with right.popover("History", icon=":material/history:", width="stretch"):
    runs = list_runs()
    if not runs:
        st.caption("No runs yet. Launch the team and every run lands here.")
    for run in runs:
        st.button(
            f"{run.idea}  \n:gray[{run.created_at:%m-%d %H:%M} · {run.tone}]",
            key=f"run-{run.id}",
            icon=":material/check_circle:" if run.ok else ":material/error:",
            on_click=open_run,
            args=(run.id,),
            width="stretch",
        )

examples = st.columns([1, 4, 4, 4], vertical_alignment="center")
examples[0].markdown('<span class="muted">Try</span>', unsafe_allow_html=True)
for column, example in zip(examples[1:], EXAMPLES, strict=True):
    column.button(
        example, type="tertiary", on_click=lambda e=example: state.update(idea=e), width="stretch"
    )

tones = st.cache_data(load_tones)()
picked = st.pills(
    "Tone skill", range(len(tones)), format_func=lambda i: tones[i].label, default=0, required=True
)
tone = tones[picked]
st.caption(tone.description)

idea = state.idea.strip()
if launched and not idea:
    st.toast("Describe your startup idea first.", icon=":material/edit:")
    launched = False
if launched:
    state.results = {}
    state.run_tone = tone.name
results: dict[str, AgentResult] = state.results


def succeeded() -> bool:
    return len(results) == len(AGENTS) and all(r.ok for r in results.values())


stepper = st.empty()


def render_stepper(stage: int) -> None:
    # stage: 0 idle, 1..len(STEPS) the step in progress, len(STEPS) + 1 when all done
    items = []
    for i, label in enumerate(STEPS, start=1):
        cls = "done" if i < stage else "active" if i == stage else ""
        items.append(f'<div class="step {cls}"><span>{i}</span>{label}</div>')
    stepper.markdown(f'<div class="stepper">{"".join(items)}</div>', unsafe_allow_html=True)


def head(key: str, cls: str, label: str) -> str:
    agent = AGENTS[key]
    return (
        f'<div class="agent-head"><div class="agent-icon">{ICONS[key]}</div>'
        f'<div><h3>{agent.title}</h3><div class="agent-role">{agent.role}</div></div>'
        f'<span class="pill {cls}">{label}</span></div>'
    )


def downloads(outputs: list[Output], prefix: str) -> None:
    for out in outputs:
        st.download_button(
            out.name,
            out.data,
            file_name=out.name,
            mime=out.mimetype,
            key=f"{prefix}-{out.name}",
            icon=":material/download:",
            on_click="ignore",
            width="stretch",
        )


def render_result(card: dict, result: AgentResult) -> None:
    if not result.ok:
        card["head"].markdown(head(result.agent, "error", "Failed"), unsafe_allow_html=True)
        card["result"].error(result.text, icon=":material/error:")
        return
    card["head"].markdown(
        head(result.agent, "done", f"Done in {result.elapsed:.0f}s"), unsafe_allow_html=True
    )
    with card["result"].container():
        for out in result.outputs:
            if out.is_image:
                st.image(out.data, width="stretch")
        downloads([o for o in result.outputs if not o.is_image], result.agent)
        with st.container(height=380, border=False):
            st.markdown(result.text)


cards = {}
for column, key in zip(st.columns(len(AGENTS)), AGENTS, strict=True):
    with column.container(border=True):
        card = cards[key] = {
            "head": st.empty(),
            "log": st.empty(),
            "result": st.empty(),
            "rows": {},
        }
        if key in results:
            render_result(card, results[key])
        else:
            card["head"].markdown(head(key, "", "Waiting"), unsafe_allow_html=True)
            hint = "Starts first" if key == RESEARCHER.key else "Starts when research is in"
            card["log"].markdown(f'<p class="idle">{hint}</p>', unsafe_allow_html=True)

kit = st.empty()


def render_kit() -> None:
    outputs = [out for result in results.values() for out in result.outputs]
    if not outputs:
        return
    research = results.get(RESEARCHER.key)
    name = brand_name(research.text) if research else "Your startup"
    logo = next((o for o in outputs if o.is_image), None)
    files = [o for o in outputs if not o.is_image]
    with kit.container(border=True):
        logo_col, info_col = st.columns([1, 3], vertical_alignment="center")
        if logo:
            logo_col.image(logo.data, width="stretch")
        with info_col:
            st.markdown(
                f'<h2 class="kit-name">{html.escape(name)}</h2>'
                f'<p class="muted">Startup kit for "{html.escape(state.idea)}", '
                f"written in the {html.escape(state.run_tone)} tone.</p>",
                unsafe_allow_html=True,
            )
            for column, out in zip(st.columns(max(len(files), 1)), files, strict=False):
                with column:
                    downloads([out], "kit")


def on_update(update: AgentEvent | AgentResult) -> None:
    card = cards[update.agent]
    if isinstance(update, AgentResult):
        results[update.agent] = update
        render_result(card, update)
        return
    if not card["rows"]:  # first event of this agent
        render_stepper(1 if update.agent == RESEARCHER.key else 2)
        card["head"].markdown(head(update.agent, "running", "Working"), unsafe_allow_html=True)
    card["rows"][update.key] = update
    rows = "".join(
        f'<li class="{e.status}"><b>{e.kind}</b>{html.escape(e.text)}</li>'
        for e in card["rows"].values()
    )
    card["log"].markdown(f'<ul class="log">{rows}</ul>', unsafe_allow_html=True)


if launched:
    render_stepper(1)
    asyncio.run(run_studio(idea, tone, on_update))
    if results:
        save_run(idea, tone.name, results)
    # Rerun so the History popover, drawn above, picks up the run just saved.
    state.celebrate = succeeded()
    st.rerun()
if state.pop("celebrate", False):
    st.balloons()
render_stepper(len(STEPS) + 1 if succeeded() else 0)
render_kit()
