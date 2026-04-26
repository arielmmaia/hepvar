"""Disk-backed key-value cache + fixture override for offline demo.

When `HEPVAR_DEMO_MODE=1`, every cache miss falls through to the on-disk fixtures dir
(`evidence/fixtures/<variant_key>/<source>.json`) before any network call. This guarantees
the demo runs offline-safely.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable

import diskcache

from backend.config import get_settings


_cache: diskcache.Cache | None = None


def _get_cache() -> diskcache.Cache:
    global _cache
    if _cache is None:
        s = get_settings()
        Path(s.cache_dir).mkdir(parents=True, exist_ok=True)
        _cache = diskcache.Cache(s.cache_dir)
    return _cache


def variant_key(chrom: str, pos: int, ref: str, alt: str, assembly: str = "GRCh38") -> str:
    return f"{assembly}_{chrom}_{pos}_{ref}_{alt}"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def fixture_path(variant_key_str: str, source: str) -> Path:
    s = get_settings()
    return Path(s.fixtures_dir) / variant_key_str / f"{source}.json"


def load_fixture(variant_key_str: str, source: str) -> dict | None:
    p = fixture_path(variant_key_str, source)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def save_fixture(variant_key_str: str, source: str, data: dict) -> None:
    p = fixture_path(variant_key_str, source)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str))


async def cached_fetch(
    *,
    variant_key_str: str,
    source: str,
    fetcher: Callable[[], Awaitable[dict]],
    ttl_seconds: int = 60 * 60 * 24 * 7,
    persist_fixture: bool = False,
) -> dict:
    """Cache-then-fixture-then-network pattern.

    Resolution order:
      1. demo mode + fixture exists  → fixture
      2. diskcache hit               → cached
      3. fetcher()                   → network; cached + optional fixture write
    """
    s = get_settings()
    cache_key = f"{variant_key_str}::{source}"

    if s.demo_mode:
        fix = load_fixture(variant_key_str, source)
        if fix is not None:
            return fix

    c = _get_cache()
    hit = c.get(cache_key)
    if hit is not None:
        return hit

    data = await fetcher()
    c.set(cache_key, data, expire=ttl_seconds)
    if persist_fixture:
        save_fixture(variant_key_str, source, data)
    return data


def write_demo_fixture_if_requested(variant_key_str: str, source: str, data: dict) -> None:
    if os.environ.get("HEPVAR_PERSIST_FIXTURES") == "1":
        save_fixture(variant_key_str, source, data)
