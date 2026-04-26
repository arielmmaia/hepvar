"""PDF export endpoint — renders the full report as a manuscript-style PDF."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.api.jobs import get_job


log = logging.getLogger(__name__)
router = APIRouter()


_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).resolve().parent / "templates")),
    autoescape=select_autoescape(["html"]),
    trim_blocks=False,
    lstrip_blocks=False,
)


@router.get("/jobs/{job_id}/pdf")
async def report_pdf(job_id: str) -> Response:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")

    report = job.report
    ev = report.get("evidence", {})
    synthesis = report.get("synthesis") or {}

    template = _env.get_template("report.html.j2")
    html = template.render(
        ev=_DotDict.wrap(ev),
        synthesis=_DotDict.wrap(synthesis) if synthesis else None,
        generated_at_str=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Lazy import — WeasyPrint is heavy and only needed for PDF rendering.
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"weasyprint not installed: {exc}")

    pdf_bytes = HTML(string=html).write_pdf()
    safe_var = f"{ev.get('variant', {}).get('chrom', 'var')}_{ev.get('variant', {}).get('pos', '?')}_{ev.get('variant', {}).get('ref', '')}_{ev.get('variant', {}).get('alt', '')}"
    fname = f"hepvar_{safe_var}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/jobs/{job_id}/preview")
async def report_html_preview(job_id: str) -> Response:
    """Same template rendered as HTML — lets you preview the report layout."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")

    ev = (job.report or {}).get("evidence", {})
    synthesis = (job.report or {}).get("synthesis") or {}
    template = _env.get_template("report.html.j2")
    html = template.render(
        ev=_DotDict.wrap(ev),
        synthesis=_DotDict.wrap(synthesis) if synthesis else None,
        generated_at_str=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )
    return Response(content=html, media_type="text/html")


class _DotDict:
    """Wraps a dict so Jinja can access keys as attributes (`ev.annotation.gene_symbol`)
    without needing to know the structure ahead of time."""

    @classmethod
    def wrap(cls, obj):
        if isinstance(obj, dict):
            return cls(obj)
        if isinstance(obj, list):
            return [cls.wrap(x) for x in obj]
        return obj

    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, name):
        if name.startswith("_") or name == "items":
            return self.__getattribute__(name)
        if name not in self._d:
            return None
        return _DotDict.wrap(self._d[name])

    def __bool__(self):
        return bool(self._d)

    def __iter__(self):
        return iter([_DotDict.wrap(x) for x in self._d])

    def __len__(self):
        return len(self._d)

    def get(self, key, default=None):
        v = self._d.get(key, default)
        return _DotDict.wrap(v) if v is not None else default

    def items(self):
        for k, v in self._d.items():
            yield k, _DotDict.wrap(v)

    def values(self):
        for v in self._d.values():
            yield _DotDict.wrap(v)

    def keys(self):
        return self._d.keys()
