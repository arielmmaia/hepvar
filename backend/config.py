from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = None
    ncbi_api_key: str | None = None
    ncbi_email: str = "hepvar@example.com"
    alphagenome_api_key: str | None = None

    @staticmethod
    def _looks_real(value: str | None) -> bool:
        """Reject obvious placeholders like 'sk-ant-...', '...', 'CHANGEME', empty."""
        if not value:
            return False
        v = value.strip()
        if not v or v in ("...", "CHANGEME"):
            return False
        if v.endswith("..."):
            return False
        return True

    demo_mode: bool = False
    cache_dir: str = ".cache"
    log_level: str = "INFO"
    allowed_origin: str = "http://localhost:3000"

    opus_model: str = "claude-opus-4-7"
    thinking_budget_tokens: int = 8000

    fixtures_dir: str = str(REPO_ROOT / "evidence" / "fixtures")
    gene_panel_path: str = str(REPO_ROOT / "backend" / "data" / "gene_panel.json")

    def __init__(self, **values):
        for env_alias, attr in (
            ("HEPVAR_DEMO_MODE", "demo_mode"),
            ("HEPVAR_CACHE_DIR", "cache_dir"),
            ("HEPVAR_LOG_LEVEL", "log_level"),
            ("ALLOWED_ORIGIN", "allowed_origin"),
        ):
            v = os.environ.get(env_alias)
            if v is not None and attr not in values:
                values[attr] = v
        super().__init__(**values)


@lru_cache
def get_settings() -> Settings:
    return Settings()
