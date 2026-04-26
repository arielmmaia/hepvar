"""Lookup module for amino-acid physicochemical properties + WT/variant comparison."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shared.schemas import AAProperty, AASubstitution


@lru_cache
def _table() -> dict[str, dict]:
    p = Path(__file__).resolve().parent.parent / "data" / "aa_properties.json"
    raw = json.loads(p.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def aa_property(code: str) -> AAProperty | None:
    if not code:
        return None
    code = code.upper()[:1]
    entry = _table().get(code)
    if entry is None:
        return None
    return AAProperty(code=code, **{k: v for k, v in entry.items() if k != "code"})


def compare(ref: str | None, alt: str | None) -> AASubstitution | None:
    if not ref or not alt:
        return None
    a = aa_property(ref)
    b = aa_property(alt)
    if a is None or b is None:
        return None
    flags: list[str] = []
    dvol = (b.volume or 0) - (a.volume or 0)
    dhyd = (b.hydrophobicity or 0) - (a.hydrophobicity or 0)
    dchg = (b.charge or 0) - (a.charge or 0)
    if abs(dvol) > 60:
        flags.append(f"volume {'shrinks' if dvol < 0 else 'grows'} by {abs(dvol):.0f} Å³ — local steric perturbation")
    if abs(dhyd) > 2.5:
        flags.append(f"polarity {'becomes more hydrophobic' if dhyd > 0 else 'becomes more hydrophilic'} (Δ{dhyd:+.1f})")
    if dchg != 0:
        flags.append(f"net charge changes by {dchg:+d}")
    if a.aromatic and not b.aromatic:
        flags.append("loss of aromatic ring (no π-stacking)")
    if not a.aromatic and b.aromatic:
        flags.append("gain of aromatic ring")
    if not a.sulfur and b.sulfur and b.code == "C":
        flags.append("introduces a free thiol — may form aberrant disulfide bonds")
    if a.code == "P" and b.code != "P":
        flags.append("removes a proline kink — local backbone gains flexibility")
    if a.code != "P" and b.code == "P":
        flags.append("introduces proline — alpha-helix breaker, rigid backbone")
    if a.code == "G" or b.code == "G":
        if a.code == "G":
            flags.append("loss of glycine flexibility — backbone constrained")
        else:
            flags.append("introduces glycine — backbone flexibility increased")
    return AASubstitution(
        wild_type=a,
        variant=b,
        delta_volume=round(dvol, 1) if dvol is not None else None,
        delta_hydrophobicity=round(dhyd, 1) if dhyd is not None else None,
        delta_charge=dchg,
        summary_flags=flags,
    )
