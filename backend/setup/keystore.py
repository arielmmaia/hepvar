"""Persist HepVar API keys to .env and validate them against each provider.

Provider mapping:
    anthropic   → ANTHROPIC_API_KEY    → validated via anthropic.AsyncAnthropic.models.list()
    ncbi        → NCBI_API_KEY         → validated via NCBI Entrez esearch ping
    alphagenome → ALPHAGENOME_API_KEY  → validated via alphagenome.dna_client.create()
                                          (a no-op call that exercises auth)

The chat layer never touches this module: keys go from the frontend KeyForm
directly into a non-LLM POST /api/setup/keys handler that calls write_key()
here. The wizard chat is a separate code path that only ever sees the *names*
of missing providers, never the values.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from threading import Lock
from typing import Literal

from backend.config import REPO_ROOT, get_settings, reload_settings


log = logging.getLogger(__name__)

Provider = Literal["anthropic", "ncbi", "alphagenome"]

ENV_PATH = REPO_ROOT / ".env"
_FILE_LOCK = Lock()

# Provider → env-var name on disk
_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "ncbi": "NCBI_API_KEY",
    "alphagenome": "ALPHAGENOME_API_KEY",
}


def env_var_for(provider: str) -> str:
    if provider not in _ENV_VARS:
        raise ValueError(f"unknown provider: {provider}")
    return _ENV_VARS[provider]


def is_placeholder(value: str | None) -> bool:
    """Match the same heuristic Settings._looks_real uses, but without needing a
    Settings instance — used while updating .env in-place."""
    if not value:
        return True
    v = value.strip()
    if not v or v in ("...", "CHANGEME"):
        return True
    if v.endswith("..."):
        return True
    return False


def write_key(provider: str, value: str) -> None:
    """Update or append a single key in .env atomically. Trailing whitespace and
    surrounding quotes on the user-pasted value are stripped before writing."""
    var = env_var_for(provider)
    cleaned = value.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("empty key value")

    line = f"{var}={cleaned}\n"
    with _FILE_LOCK:
        if ENV_PATH.exists():
            content = ENV_PATH.read_text().splitlines(keepends=False)
        else:
            content = []
        out: list[str] = []
        replaced = False
        for raw in content:
            stripped = raw.lstrip()
            if stripped.startswith("#") or "=" not in stripped:
                out.append(raw)
                continue
            key_name = stripped.split("=", 1)[0].strip()
            if key_name == var:
                out.append(f"{var}={cleaned}")
                replaced = True
            else:
                out.append(raw)
        if not replaced:
            out.append(f"{var}={cleaned}")
        ENV_PATH.write_text("\n".join(out) + "\n")
    # Refresh the cached Settings so subsequent requests see the new value.
    reload_settings()


# ---------- validation ----------

async def _validate_anthropic(key: str) -> tuple[bool, str | None]:
    try:
        import anthropic  # type: ignore
    except ImportError:
        return False, "anthropic SDK not installed"
    try:
        client = anthropic.AsyncAnthropic(api_key=key)
        # /v1/models is the cheapest authenticated endpoint.
        await client.models.list(limit=1)
        return True, None
    except anthropic.AuthenticationError:
        return False, "invalid API key (401)"
    except Exception as exc:
        return False, str(exc)[:200]


async def _validate_ncbi(key: str) -> tuple[bool, str | None]:
    import httpx
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    s = get_settings()
    params = {
        "db": "pubmed",
        "term": "ABCB4",
        "retmax": 1,
        "retmode": "json",
        "tool": "hepvar",
        "email": s.ncbi_email,
        "api_key": key,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
        if r.status_code == 400:
            # NCBI returns 400 with body {"error": "API key invalid"} for bad keys
            try:
                body = r.json()
                if "api" in (body.get("error") or "").lower():
                    return False, "invalid NCBI API key"
            except Exception:
                pass
            return False, f"NCBI returned {r.status_code}: {r.text[:200]}"
        if r.status_code != 200:
            return False, f"NCBI returned {r.status_code}"
        return True, None
    except Exception as exc:
        return False, str(exc)[:200]


async def _validate_alphagenome(key: str) -> tuple[bool, str | None]:
    try:
        from alphagenome.models import dna_client  # type: ignore
    except ImportError:
        return False, "alphagenome SDK not installed"

    def _probe():
        # Construct the client and call any auth-exercising method. We use a
        # cheap interval to avoid spending any actual prediction quota.
        try:
            client = dna_client.create(key)
            # `output_metadata` is a metadata-only call that still requires auth.
            client.output_metadata()
            return True, None
        except Exception as exc:
            msg = str(exc)
            if "API key" in msg or "PERMISSION" in msg or "UNAUTH" in msg.upper():
                return False, "invalid AlphaGenome API key"
            return False, msg[:200]

    return await asyncio.to_thread(_probe)


async def validate_key(provider: str, key: str) -> tuple[bool, str | None]:
    """Returns (ok, error_message). Network calls; tolerant of provider downtime."""
    if not key or is_placeholder(key):
        return False, "missing or placeholder value"
    if provider == "anthropic":
        return await _validate_anthropic(key)
    if provider == "ncbi":
        return await _validate_ncbi(key)
    if provider == "alphagenome":
        return await _validate_alphagenome(key)
    return False, f"unknown provider: {provider}"


def current_status() -> dict[str, str]:
    """Returns provider → 'valid' | 'missing' | 'unknown' (configured but not validated).

    Configured-but-not-validated maps to 'unknown' because we don't want to fire
    validation pings on every status request. The frontend can call POST
    /api/setup/validate/{provider} when it wants a live check.
    """
    s = get_settings()
    out: dict[str, str] = {}
    for prov, var in _ENV_VARS.items():
        val = getattr(s, _SETTINGS_ATTR[prov], None)
        out[prov] = "missing" if not s._looks_real(val) else "configured"
    return out


_SETTINGS_ATTR: dict[str, str] = {
    "anthropic": "anthropic_api_key",
    "ncbi": "ncbi_api_key",
    "alphagenome": "alphagenome_api_key",
}
