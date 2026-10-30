from __future__ import annotations

from cominty_sdk import (
    AgentCapabilities,
    ImageGenerationCapability,
    McpCapability,
    SkillsCapability,
    WebCapability,
)

from studio.schemas import Agent


def _caps(
    web: bool = False, image: bool = False, skills: bool = False, mcp: bool = False
) -> AgentCapabilities:
    # Each agent gets only its own tools, so the stream shows a clear division of labor.
    return AgentCapabilities(
        web=WebCapability(activation="always" if web else "never"),
        image_generation=ImageGenerationCapability(activation="always" if image else "never"),
        skills=SkillsCapability(activation="always" if skills else "never"),
        # "on_request" would stay off unless each message enabled it: use "always".
        mcp=McpCapability(activation="always" if mcp else "never"),
    )


RESEARCHER = Agent(
    key="researcher",
    title="Researcher",
    role="Web search",
    capabilities=_caps(web=True),
    prompt="""You are the market researcher of a startup studio.
Startup idea: {idea}

Search the web. Reply in concise Markdown (max 250 words),
with no preamble and no notes about your process. Your reply must start with "**Name:**".
- **Name:** a short catchy brand name for the startup.
- Target audience.
- 3-5 real competitors, each with a link.
- Market size estimate with a source.
- The one gap this startup should own.""",
)

DESIGNER = Agent(
    key="designer",
    title="Designer",
    role="Image generation",
    capabilities=_caps(image=True),
    prompt="""You are the brand designer of a startup studio.
Startup idea: {idea}
Research (use the brand name from it):
{research}

Generate ONE logo image: minimal, flat, vector style, white background, and present it.
Then reply briefly in Markdown: the name, a tagline, and a 3-color palette (hex).""",
)

PM = Agent(
    key="pm",
    title="Product Manager",
    role="Spreadsheet skill + Linear",
    capabilities=_caps(skills=True, mcp=True),
    prompt="""You are the product manager of a startup studio.
Startup idea: {idea}
Research:
{research}

Plan the MVP as 6-8 issues. Using your spreadsheet skill, create and present the file
backlog.xlsx with columns: ID, Title, Description, Priority, Estimate (days), Owner role.
Then, using the Linear integration, create the same issues in the first Linear team, with
title, description and priority. Then reply in Markdown with the backlog as a short table
that includes each Linear issue identifier as a link. If Linear is unavailable, say so.""",
)

WRITER = Agent(
    key="writer",
    title="Pitch Writer",
    role="Slides skill + PDF",
    capabilities=_caps(skills=True),
    export_pdf="pitch.pdf",
    prompt="""You are the pitch writer of a startup studio.
Startup idea: {idea}
Research:
{research}

Using your slides skill, create and present pitch.pptx: 6 slides (Problem, Solution,
Market, Competitors, Business model, The ask). Use the brand name from the research.
Then reply with the one-page pitch in Markdown, same sections, no preamble.""",
)

TEAM = (DESIGNER, PM, WRITER)
ALL_AGENTS = (RESEARCHER, *TEAM)
AGENTS = {a.key: a for a in ALL_AGENTS}
