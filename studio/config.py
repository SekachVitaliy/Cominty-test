from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


# Reads the process env first, then .env. Streamlit Cloud secrets and docker compose
# env_file both land in the process env, so one class covers every way of running.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    cominty_api_key: str
    cominty_user_id: str
    cominty_base_url: str | None = None
    cominty_agent_id: str = "__cominty_agents::agent.chat"
    runs_dir: Path = ROOT / "runs"
    skills_dir: Path = ROOT / "skills"


settings = Settings()  # type: ignore[call-arg]  # required fields come from the env
