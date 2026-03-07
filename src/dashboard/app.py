"""FastAPI approval dashboard for campaign drafts.

Endpoints:
- GET /        — HTML dashboard with draft list, filters, summary counts
- GET /drafts  — JSON array of all drafts
- GET /drafts/{id} — HTML detail with email preview + approve/reject buttons
- POST /drafts/{id}/approve — Mark APPROVED, push to GHL, record timestamp
- POST /drafts/{id}/reject  — Mark REJECTED, write feedback file
- POST /drafts/batch/approve — Batch approve selected drafts
- POST /drafts/batch/reject  — Batch reject selected drafts
- GET /dispatch         — Dispatch queue + history
- POST /dispatch/run    — Trigger a dispatch cycle
- GET /dispatch/status  — JSON: circuit breaker states, daily counts, KPI
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from dashboard.storage import (
    approve_draft,
    get_draft,
    list_drafts,
    reject_draft,
    update_draft_ghl_result,
)
from integrations.ghl_service import push_approved_draft_to_ghl

from models.schemas import DraftApprovalStatus
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.dispatcher import dispatch_approved_drafts
from pipeline.kpi_tracker import KPITracker
from pipeline.rate_limiter import DailyRateLimiter

app = FastAPI(title="RevTry Dashboard", version="0.3.0")

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
) -> HTMLResponse:
    drafts = list_drafts()

    if tier:
        drafts = [d for d in drafts if d.icp_tier == tier]
    if status:
        drafts = [d for d in drafts if d.status.value == status]
    if channel:
        drafts = [d for d in drafts if d.channel.value == channel]
    if search:
        q = search.lower()
        drafts = [
            d for d in drafts
            if q in d.contact_id.lower() or q in d.subject.lower()
        ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "drafts": drafts,
            "filter_tier": tier or "",
            "filter_status": status or "",
            "filter_channel": channel or "",
            "search": search or "",
        },
    )


@app.get("/drafts")
async def list_drafts_api():
    drafts = list_drafts()
    return [d.model_dump(by_alias=True) for d in drafts]


# Batch routes MUST be defined before {draft_id} routes to avoid path conflicts
@app.post("/drafts/batch/approve")
async def batch_approve(draft_ids: str = Form("")):
    ids = [i.strip() for i in draft_ids.split(",") if i.strip()]
    for did in ids:
        draft = approve_draft(did)
        if draft:
            ghl_result = await push_approved_draft_to_ghl(draft)
            update_draft_ghl_result(did, ghl_result)
    return RedirectResponse(url="/", status_code=303)


@app.post("/drafts/batch/reject")
async def batch_reject(draft_ids: str = Form(""), reason: str = Form("")):
    ids = [i.strip() for i in draft_ids.split(",") if i.strip()]
    for did in ids:
        reject_draft(did, reason=reason)
    return RedirectResponse(url="/", status_code=303)


@app.get("/drafts/{draft_id}", response_class=HTMLResponse)
async def draft_detail(request: Request, draft_id: str) -> HTMLResponse:
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return templates.TemplateResponse(
        "draft_detail.html",
        {"request": request, "draft": draft},
    )


@app.post("/drafts/{draft_id}/approve")
async def approve_draft_endpoint(draft_id: str):
    draft = approve_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Best-effort GHL push — approval stands even if this fails
    ghl_result = await push_approved_draft_to_ghl(draft)
    update_draft_ghl_result(draft_id, ghl_result)

    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.post("/drafts/{draft_id}/reject")
async def reject_draft_endpoint(draft_id: str, reason: str = Form("")):
    draft = reject_draft(draft_id, reason=reason)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


# ── Dispatch Endpoints ─────────────────────────────────────────────────────────


@app.get("/dispatch", response_class=HTMLResponse)
async def dispatch_view(request: Request) -> HTMLResponse:
    """Show dispatch queue (APPROVED drafts) and recent dispatch history."""
    all_drafts = list_drafts()
    queue = [d for d in all_drafts if d.status == DraftApprovalStatus.APPROVED]
    dispatched = [d for d in all_drafts if d.status == DraftApprovalStatus.DISPATCHED]

    cb = CircuitBreaker()
    rl = DailyRateLimiter()
    kpi = KPITracker(circuit_breaker=cb)

    return templates.TemplateResponse(
        "dispatch.html",
        {
            "request": request,
            "queue": queue,
            "dispatched": dispatched,
            "cb_states": cb.get_all_states(),
            "daily_counts": rl.get_counts(),
            "daily_limit": rl.limit,
            "kpi": kpi.get_latest_kpi(),
        },
    )


@app.post("/dispatch/run")
async def dispatch_run():
    """Trigger a dispatch cycle."""
    result = await dispatch_approved_drafts()
    return {
        "dispatched": result.dispatched,
        "skipped_dedup": result.skipped_dedup,
        "skipped_rate_limit": result.skipped_rate_limit,
        "skipped_circuit_breaker": result.skipped_circuit_breaker,
        "skipped_tier": result.skipped_tier,
        "failed": result.failed,
        "errors": result.errors,
    }


@app.get("/dispatch/status")
async def dispatch_status():
    """JSON: circuit breaker states, daily counts, KPI summary."""
    cb = CircuitBreaker()
    rl = DailyRateLimiter()
    kpi = KPITracker(circuit_breaker=cb)
    snapshot = kpi.get_latest_kpi()

    return {
        "circuit_breakers": cb.get_all_states(),
        "daily_counts": rl.get_counts(),
        "daily_limit": rl.limit,
        "kpi": {
            "sent": snapshot.sent_count if snapshot else 0,
            "opens": snapshot.open_count if snapshot else 0,
            "replies": snapshot.reply_count if snapshot else 0,
            "bounces": snapshot.bounce_count if snapshot else 0,
            "unsubs": snapshot.unsub_count if snapshot else 0,
            "emergency_stop": snapshot.emergency_stop if snapshot else False,
            "violations": snapshot.violations if snapshot else [],
        } if snapshot else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
