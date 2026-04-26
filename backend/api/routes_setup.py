"""Setup-wizard endpoints. The chat layer never touches these — keys go from
the SetupWizard form straight to /api/setup/keys, which writes .env on disk."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.setup.keystore import (
    Provider,
    current_status,
    validate_key,
    write_key,
)


log = logging.getLogger(__name__)
router = APIRouter()


class KeyPayload(BaseModel):
    provider: str = Field(..., description="anthropic | ncbi | alphagenome")
    value: str = Field(..., description="the API key as the user pasted it")


class StatusResponse(BaseModel):
    anthropic: str  # "missing" | "configured"
    ncbi: str
    alphagenome: str
    all_ready: bool


class SaveResponse(BaseModel):
    ok: bool
    provider: str
    error: str | None = None


@router.get("/setup/status", response_model=StatusResponse)
async def setup_status() -> StatusResponse:
    """Cheap status — does not run validation pings. Use validate/{provider} for that."""
    s = current_status()
    return StatusResponse(
        anthropic=s.get("anthropic", "missing"),
        ncbi=s.get("ncbi", "missing"),
        alphagenome=s.get("alphagenome", "missing"),
        all_ready=all(v == "configured" for v in s.values()),
    )


@router.post("/setup/keys", response_model=SaveResponse)
async def save_key(payload: KeyPayload) -> SaveResponse:
    """Validate a key against the provider, then write it to .env if it works.

    The chat layer never calls this endpoint. The frontend KeyForm posts here
    directly. We log only the provider name and the validation outcome — the
    key value never appears in logs or returned responses.
    """
    if payload.provider not in ("anthropic", "ncbi", "alphagenome"):
        raise HTTPException(status_code=400, detail=f"unknown provider: {payload.provider}")

    ok, err = await validate_key(payload.provider, payload.value)
    if not ok:
        log.info("setup/keys validation failed for %s: %s", payload.provider, err)
        return SaveResponse(ok=False, provider=payload.provider, error=err or "validation failed")

    try:
        write_key(payload.provider, payload.value)
    except Exception as exc:
        log.exception("setup/keys write failed for %s", payload.provider)
        return SaveResponse(ok=False, provider=payload.provider, error=f"could not write .env: {exc}")
    log.info("setup/keys saved %s (validated)", payload.provider)
    return SaveResponse(ok=True, provider=payload.provider)


@router.post("/setup/validate/{provider}", response_model=SaveResponse)
async def validate_existing_key(provider: str) -> SaveResponse:
    """Re-validate the *currently stored* key for a provider — used to refresh
    status icons in the wizard without re-entering the value."""
    if provider not in ("anthropic", "ncbi", "alphagenome"):
        raise HTTPException(status_code=400, detail=f"unknown provider: {provider}")
    from backend.config import get_settings
    s = get_settings()
    attrs = {"anthropic": "anthropic_api_key", "ncbi": "ncbi_api_key", "alphagenome": "alphagenome_api_key"}
    val = getattr(s, attrs[provider], None)
    if not val or not s._looks_real(val):
        return SaveResponse(ok=False, provider=provider, error="no key configured")
    ok, err = await validate_key(provider, val)
    return SaveResponse(ok=ok, provider=provider, error=err)
