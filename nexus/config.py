"""NEXUS configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class NexusConfig(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = {"env_prefix": "NEXUS_", "env_file": ".env", "extra": "ignore"}

    # LLM -----------------------------------------------------------
    default_model: str = "claude-sonnet-4-6"

    # Resource limits -----------------------------------------------
    max_agents: int = 10
    token_budget_per_task: int = 100_000
    tool_creation_timeout: int = 30

    # Ports ---------------------------------------------------------
    api_port: int = 8000
    dashboard_port: int = 3000

    # Workspace -----------------------------------------------------
    workspace_dir: Path = Path("./workspace")

    # Approval flags ------------------------------------------------
    require_approval_for_tools: bool = True
    require_approval_for_shell: bool = True

    # Logging -------------------------------------------------------
    log_level: str = "INFO"


# Singleton — import this everywhere
_config: NexusConfig | None = None


def get_config() -> NexusConfig:
    global _config
    if _config is None:
        _config = NexusConfig()
    return _config
