# Startup Studio

Type one sentence. A team of four Cominty Managed Agents turns it into a startup kit:
market research, a logo, an MVP backlog spreadsheet, and a pitch deck plus PDF.
Pick a **tone skill** and every agent writes in that voice.

## Scenario

1. **Researcher** (web search) finds real competitors with links, sizes the market,
   and proposes a brand name.
2. Then three agents run **in parallel**, all fed with the research:
   - **Designer** (image generation) draws the logo and picks a tagline and palette.
   - **Product Manager** (platform `spreadsheet` skill) builds `backlog.xlsx`. If a
     tracker MCP (Linear, Jira) is connected to the org, it files the issues there too.
   - **Pitch Writer** (platform `slides` skill) builds `pitch.pptx`, and the reply is
     exported to `pitch.pdf`.

Every tool call streams live into the agent's card, so you watch the team work.

## Integration

All agent work goes through the Cominty Python SDK (`cominty-sdk`):

| SDK call | Used for |
|---|---|
| `chat.start(..., thread_capabilities=...)` | one thread per agent, only its own tools on |
| iterating the run (`events.ToolCall`, ...) | the live activity log in each card |
| `run.result()` | final reply and generated files |
| `chat.download_file` | logo, `.xlsx`, `.pptx` |
| `chat.export(format="pdf")` | the pitch PDF |

## Layout

```
app.py                Streamlit UI
studio/config.py      settings from env / .env (pydantic-settings)
studio/schemas.py     Agent, Tone, events/results, run.json records
studio/exceptions.py  StudioError, AgentFailed, ToneSkillError
studio/agents.py      the four agents: prompt + capabilities
studio/pipeline.py    runs the team, streams updates
studio/history.py     saves and loads runs (runs/<id>/)
studio/tones.py       loads tone skills
skills/*.md           tone skills (add a file to add a tone)
assets/style.css      styles
```

A tone skill is a Markdown file (`icon` is a Material Symbols name):

```markdown
---
name: Bold founder
icon: local_fire_department
description: High energy, punchy, visionary.
---
- Write like a founder on stage ...
```

## Run locally

```bash
cp .env.example .env               # fill COMINTY_API_KEY, COMINTY_USER_ID
docker compose up --build            # http://localhost:8501
```

Without Docker: `pip install -r requirements.txt && streamlit run app.py`.

## Linear

The PM agent creates issues in Linear through the platform's MCP integration: no Linear
code or token lives in this app. Connect it once in platform.cominty.ai, Administration,
Integrations, Linear. The PM agent has MCP on `on_request` and picks it up on the next run.

## Deploy

Any Docker host works (Render, Railway, Fly): the image honours `$PORT`.

### Streamlit Community Cloud

1. Push this folder to a GitHub repo.
2. share.streamlit.io: New app, pick the repo, main file `app.py`.
3. Settings, Secrets:
   ```toml
   COMINTY_API_KEY = "sk-cmt-..."
   COMINTY_USER_ID = "user_..."
   ```
   Root-level secrets are exposed as environment variables, which the SDK reads.

The demo has no login: anyone with the URL spends your credits. Keep the link private.
