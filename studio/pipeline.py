from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable

from cominty_sdk import (
    APIConnectionError,
    AsyncCominty,
    ComintyError,
    RateLimitError,
    ServerError,
    events,
)

from studio.agents import RESEARCHER, TEAM
from studio.config import settings
from studio.exceptions import AgentFailed
from studio.schemas import Agent, AgentEvent, AgentResult, EventKind, Output, Tone

OnUpdate = Callable[[AgentEvent | AgentResult], None]


def clean(text: str) -> str:
    # The web tool sometimes leaks <cite url="..."> tags: turn them into Markdown links.
    text = re.sub(r'<cite url="([^"]+)">(.*?)</cite>', r"[\2](\1)", text, flags=re.S)
    return re.sub(r"</?cite[^>]*>", "", text)


def brand_name(research: str) -> str:
    # The researcher's prompt makes "**Name:**" its first line.
    match = re.search(r"\*\*Name:\*\*\s*([^\n(]+)", research)  # stop before "(or ...)"
    return match.group(1).strip().strip("*") if match else "Your startup"


def describe(event: events.AnyEvent) -> tuple[EventKind, str]:
    if isinstance(event, events.ToolCall):
        return "tool", f"{event.data.name}: {event.data.description}"
    if isinstance(event, events.IntermediaryUpdate):
        return "note", event.data.message
    if isinstance(event, events.LlmStep):
        return "think", event.data.model
    return "step", event.name.replace("_", " ")


_TRANSIENT = (APIConnectionError, RateLimitError, ServerError)


async def _retry[T](call: Callable[[], Awaitable[T]], attempts: int = 3) -> T:
    # Only for idempotent reads (download, export). Never wrap chat.start: a retry there
    # would open a second thread and repeat the agent's side effects (Linear issues).
    for attempt in range(1, attempts):
        try:
            return await call()
        except _TRANSIENT:
            await asyncio.sleep(2**attempt)
    return await call()


async def _run_agent(
    client: AsyncCominty, agent: Agent, idea: str, tone: Tone, research: str, on_update: OnUpdate
) -> str | None:
    started_at = time.monotonic()
    try:
        started = await client.chat.start(
            agent_id=settings.cominty_agent_id,
            message=agent.render(idea, tone, research),
            name=f"[{agent.key}] {idea[:60]}",
            thread_capabilities=agent.capabilities,
        )
        async for event in started:
            on_update(AgentEvent(agent.key, event.correlation_id, event.status, *describe(event)))
        message = await started.result()
        if message.status != "success":
            raise AgentFailed(agent.key, message.error_code or message.status)
        downloads = asyncio.gather(
            *(_retry(lambda f=f: client.chat.download_file(f.id)) for f in message.files)
        )
        if agent.export_pdf:
            export = _retry(lambda: client.chat.export(message.id, format="pdf"))
            blobs, pdf = await asyncio.gather(downloads, export, return_exceptions=True)
        else:
            blobs, pdf = await downloads, None
        if isinstance(blobs, BaseException):
            raise blobs
    except (ComintyError, AgentFailed) as exc:
        on_update(AgentResult(agent.key, False, str(exc), time.monotonic() - started_at))
        return None
    text = clean(message.content)
    outputs = [
        Output(f.name, f.mimetype, data) for f, data in zip(message.files, blobs, strict=True)
    ]
    if isinstance(pdf, bytes):
        outputs.append(Output(agent.export_pdf or "", "application/pdf", pdf))
    elif pdf is not None:
        # The reply itself succeeded: keep it and the other files, flag only the PDF.
        text += f"\n\n_PDF export failed: {pdf}_"
    on_update(AgentResult(agent.key, True, text, time.monotonic() - started_at, outputs))
    return text


async def run_studio(idea: str, tone: Tone, on_update: OnUpdate) -> None:
    async with AsyncCominty(
        api_token=settings.cominty_api_key,
        user_id=settings.cominty_user_id,
        base_url=settings.cominty_base_url,
        timeout=settings.cominty_timeout,
    ) as client:
        research = await _run_agent(client, RESEARCHER, idea, tone, "", on_update)
        if research is None:
            return  # the team builds on the research: nothing to build on
        await asyncio.gather(
            *(_run_agent(client, a, idea, tone, research, on_update) for a in TEAM)
        )
