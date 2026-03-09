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

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from dashboard.auth import (
    is_dashboard_auth_enabled,
    is_warm_only_mode,
    require_dashboard_auth,
)
from dashboard.briefing_loader import (
    load_contact_conversation,
    load_daily_briefing,
    load_followup_queue,
)
from dashboard.followup_storage import (
    approve_followup_draft,
    get_followup_draft,
    list_followup_drafts,
    reject_followup_draft,
)
from dashboard.storage import (
    approve_draft,
    get_draft,
    list_drafts,
    reject_draft,
    update_draft_ghl_result,
)
from integrations.ghl_client import MissingGhlCredentialsError
from integrations.ghl_service import push_approved_draft_to_ghl

from models.schemas import DraftApprovalStatus
from persistence.factory import get_storage_backend_name, validate_storage_configuration
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the warm scheduler only when explicitly enabled and implemented."""
    validate_storage_configuration(warm_only_mode=is_warm_only_mode())
    if is_dashboard_auth_enabled():
        if not os.environ.get("DASHBOARD_BASIC_AUTH_USER", "").strip():
            raise RuntimeError("DASHBOARD_BASIC_AUTH_USER is required when dashboard auth is enabled")
        if not os.environ.get("DASHBOARD_BASIC_AUTH_PASS", "").strip():
            raise RuntimeError("DASHBOARD_BASIC_AUTH_PASS is required when dashboard auth is enabled")

    if os.environ.get("SCHEDULER_ENABLED", "false").lower() == "true":
        try:
            from pipeline.scheduler import start_scheduler  # type: ignore
        except ImportError:
            logger.warning("SCHEDULER_ENABLED=true but pipeline.scheduler is not implemented yet")
        else:
            try:
                start_scheduler()
            except ImportError:
                logger.warning(
                    "SCHEDULER_ENABLED=true but APScheduler is not installed; skipping scheduler startup"
                )
    yield


from pipeline.circuit_breaker import CircuitBreaker
from pipeline.dispatcher import dispatch_approved_drafts
from pipeline.followup_dispatcher import dispatch_approved_followups
from pipeline.followup_orchestrator import run_followup_orchestrator
from pipeline.kpi_tracker import KPITracker
from pipeline.rate_limiter import DailyRateLimiter

app = FastAPI(title="RevTry Dashboard", version="0.3.0", lifespan=lifespan)

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["is_warm_only_mode"] = is_warm_only_mode


def _raise_if_cold_routes_disabled() -> None:
    if is_warm_only_mode():
        raise HTTPException(status_code=404, detail="Cold outbound routes are disabled in warm-only mode")


def _get_followup_queue_item(draft_id: str) -> Optional[dict]:
    for item in load_followup_queue(date=None):
        if item.get("draftId") == draft_id:
            return item
    return None


def _build_dispatch_status_payload(*, circuit_breaker: CircuitBreaker, rate_limiter: DailyRateLimiter) -> dict:
    snapshot = KPITracker(circuit_breaker=circuit_breaker).get_latest_kpi()
    return {
        "circuit_breakers": circuit_breaker.get_all_states(),
        "daily_counts": rate_limiter.get_counts(),
        "daily_limit": rate_limiter.limit,
        "kpi": {
            "sent": snapshot.sent_count if snapshot else 0,
            "opens": snapshot.open_count if snapshot else 0,
            "replies": snapshot.reply_count if snapshot else 0,
            "bounces": snapshot.bounce_count if snapshot else 0,
            "unsubs": snapshot.unsub_count if snapshot else 0,
            "emergency_stop": snapshot.emergency_stop if snapshot else False,
            "violations": snapshot.violations if snapshot else [],
        }
        if snapshot
        else None,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    if is_warm_only_mode():
        return RedirectResponse(url="/briefing", status_code=307)

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
        request,
        "dashboard.html",
        {
            "drafts": drafts,
            "filter_tier": tier or "",
            "filter_status": status or "",
            "filter_channel": channel or "",
            "search": search or "",
        },
    )


@app.get("/drafts")
async def list_drafts_api(_: None = Depends(require_dashboard_auth)):
    _raise_if_cold_routes_disabled()
    drafts = list_drafts()
    return [d.model_dump(by_alias=True) for d in drafts]


@app.get("/cold-drafts", response_class=HTMLResponse)
async def cold_drafts_alias(
    request: Request,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    _raise_if_cold_routes_disabled()
    return await dashboard(
        request=request,
        tier=tier,
        status=status,
        channel=channel,
        search=search,
    )


@app.get("/briefing", response_class=HTMLResponse)
async def briefing_view(
    request: Request,
    date: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    try:
        briefing = load_daily_briefing(date)
        queue = load_followup_queue(date)
    except Exception as exc:
        logger.exception("Failed to load briefing data")
        from utils.business_time import current_business_date
        from models.schemas import DailyBriefing
        briefing = DailyBriefing(
            date=date or current_business_date(),
            totalContactsScanned=0, contactsNeedingFollowup=0,
            contactsSkippedNoConversation=0, contactsSkippedNoEmail=0,
            hotCount=0, warmCount=0, coolingCount=0,
            noReplyCount=0, awaitingResponseCount=0, goneColdCount=0,
            draftsGenerated=0, analysisFailedCount=0, draftFailedCount=0,
            estimatedCostUsd=0.0,
            generatedAt="error",
        )
        queue = []
    return templates.TemplateResponse(
        request,
        "briefing.html",
        {
            "briefing": briefing,
            "queue": queue,
            "selected_date": briefing.date,
        },
    )


@app.get("/followups", response_class=HTMLResponse)
async def followup_list_view(
    request: Request,
    date: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    try:
        queue = load_followup_queue(date)
    except Exception:
        logger.exception("Failed to load followup queue")
        queue = []
    return templates.TemplateResponse(
        request,
        "followup_list.html",
        {
            "queue": queue,
            "selected_date": date or (queue[0]["businessDate"] if queue else None),
        },
    )


@app.post("/followups/batch/approve")
async def batch_approve_followups(
    draft_ids: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    ids = [draft_id.strip() for draft_id in draft_ids.split(",") if draft_id.strip()]
    for draft_id in ids:
        approve_followup_draft(draft_id)
    return RedirectResponse(url="/followups", status_code=303)


@app.post("/followups/batch/reject")
async def batch_reject_followups(
    draft_ids: str = Form(""),
    reason: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    ids = [draft_id.strip() for draft_id in draft_ids.split(",") if draft_id.strip()]
    for draft_id in ids:
        reject_followup_draft(draft_id, reason=reason)
    return RedirectResponse(url="/followups", status_code=303)


@app.post("/followups/generate")
async def generate_followups(
    force: bool = Form(False),
    _: None = Depends(require_dashboard_auth),
):
    result = await run_followup_orchestrator(
        task_id="warm-followup-manual",
        force=force,
    )

    status = result.get("status")
    if status in {"blocked_missing_anthropic_api_key", "blocked_missing_ghl_credentials", "circuit_open"}:
        return JSONResponse(status_code=503, content=result)

    return JSONResponse(status_code=200, content=result)


@app.get("/followups/{draft_id}", response_class=HTMLResponse)
async def followup_detail_view(
    request: Request,
    draft_id: str,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    draft = get_followup_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")

    queue_item = _get_followup_queue_item(draft_id)
    conversation = load_contact_conversation(draft.contact_id)
    return templates.TemplateResponse(
        request,
        "followup_detail.html",
        {
            "draft": draft,
            "analysis": queue_item["analysis"] if queue_item else None,
            "summary": queue_item["summary"] if queue_item else conversation,
            "primary_thread": queue_item["primaryThread"] if queue_item else None,
            "conversation": conversation,
        },
    )


@app.post("/followups/{draft_id}/approve")
async def approve_followup_endpoint(
    draft_id: str,
    _: None = Depends(require_dashboard_auth),
):
    draft = approve_followup_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    return RedirectResponse(url=f"/followups/{draft_id}", status_code=303)


@app.post("/followups/{draft_id}/reject")
async def reject_followup_endpoint(
    draft_id: str,
    reason: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    draft = reject_followup_draft(draft_id, reason=reason)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    return RedirectResponse(url=f"/followups/{draft_id}", status_code=303)


# Batch routes MUST be defined before {draft_id} routes to avoid path conflicts
@app.post("/drafts/batch/approve")
async def batch_approve(
    draft_ids: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    _raise_if_cold_routes_disabled()
    ids = [i.strip() for i in draft_ids.split(",") if i.strip()]
    for did in ids:
        draft = approve_draft(did)
        if draft:
            ghl_result = await push_approved_draft_to_ghl(draft)
            update_draft_ghl_result(did, ghl_result)
    return RedirectResponse(url="/", status_code=303)


@app.post("/drafts/batch/reject")
async def batch_reject(
    draft_ids: str = Form(""),
    reason: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    _raise_if_cold_routes_disabled()
    ids = [i.strip() for i in draft_ids.split(",") if i.strip()]
    for did in ids:
        reject_draft(did, reason=reason)
    return RedirectResponse(url="/", status_code=303)


@app.get("/drafts/{draft_id}", response_class=HTMLResponse)
async def draft_detail(
    request: Request,
    draft_id: str,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    _raise_if_cold_routes_disabled()
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return templates.TemplateResponse(
        request,
        "draft_detail.html",
        {"draft": draft},
    )


@app.post("/drafts/{draft_id}/approve")
async def approve_draft_endpoint(
    draft_id: str,
    _: None = Depends(require_dashboard_auth),
):
    _raise_if_cold_routes_disabled()
    draft = approve_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Best-effort GHL push — approval stands even if this fails
    ghl_result = await push_approved_draft_to_ghl(draft)
    update_draft_ghl_result(draft_id, ghl_result)

    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.post("/drafts/{draft_id}/reject")
async def reject_draft_endpoint(
    draft_id: str,
    reason: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    _raise_if_cold_routes_disabled()
    draft = reject_draft(draft_id, reason=reason)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "mode": "warm_only" if is_warm_only_mode() else "mixed",
        "storageBackend": get_storage_backend_name(),
    }


# ── Dispatch Endpoints ─────────────────────────────────────────────────────────


@app.get("/dispatch", response_class=HTMLResponse)
async def dispatch_view(
    request: Request,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    """Show unified warm/cold dispatch queues and recent dispatch history."""
    warm_only = is_warm_only_mode()
    warm_drafts = list_followup_drafts(latest_only=False)
    warm_queue = [draft for draft in warm_drafts if draft.status == DraftApprovalStatus.APPROVED]
    warm_dispatched = [
        draft for draft in warm_drafts if draft.status == DraftApprovalStatus.DISPATCHED
    ]
    cold_queue = []
    cold_dispatched = []
    if not warm_only:
        all_drafts = list_drafts()
        cold_queue = [d for d in all_drafts if d.status == DraftApprovalStatus.APPROVED]
        cold_dispatched = [d for d in all_drafts if d.status == DraftApprovalStatus.DISPATCHED]
    cb = CircuitBreaker()
    rl = DailyRateLimiter()
    snapshot = KPITracker(circuit_breaker=cb).get_latest_kpi()

    return templates.TemplateResponse(
        request,
        "dispatch.html",
        {
            "warm_queue": warm_queue,
            "warm_dispatched": warm_dispatched,
            "cold_queue": cold_queue,
            "cold_dispatched": cold_dispatched,
            "warm_only_mode": warm_only,
            "cb_states": cb.get_all_states(),
            "daily_counts": rl.get_counts(),
            "daily_limit": rl.limit,
            "kpi": snapshot,
        },
    )


@app.post("/dispatch/run")
async def dispatch_run(_: None = Depends(require_dashboard_auth)):
    """Trigger a unified warm-first dispatch cycle."""
    cb = CircuitBreaker()
    rl = DailyRateLimiter()
    warm_only = is_warm_only_mode()

    try:
        warm = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
        )
        if warm_only:
            cold = None
        else:
            cold = await dispatch_approved_drafts(
                rate_limiter=rl,
                circuit_breaker=cb,
            )
    except MissingGhlCredentialsError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "blocked_missing_ghl_credentials", "errors": [str(exc)]},
        )

    cold_payload = {
        "dispatched": 0,
        "skippedDedup": 0,
        "skippedRateLimit": 0,
        "skippedCircuitBreaker": 0,
        "skippedTier": 0,
        "skippedDeferredChannel": 0,
        "failed": 0,
        "errors": [],
    }
    if cold is not None:
        cold_payload = {
            "dispatched": cold.dispatched,
            "skippedDedup": cold.skipped_dedup,
            "skippedRateLimit": cold.skipped_rate_limit,
            "skippedCircuitBreaker": cold.skipped_circuit_breaker,
            "skippedTier": cold.skipped_tier,
            "skippedDeferredChannel": cold.skipped_deferred_channel,
            "failed": cold.failed,
            "errors": cold.errors,
        }

    warm_payload = {
        "dispatched": warm.dispatched,
        "skippedDedup": warm.skipped_dedup,
        "skippedRateLimit": warm.skipped_rate_limit,
        "skippedCircuitBreaker": warm.skipped_circuit_breaker,
        "failed": warm.failed,
        "errors": warm.errors,
    }
    return {
        "warm": warm_payload,
        "cold": cold_payload,
        "totals": {
            "dispatched": warm_payload["dispatched"] + cold_payload["dispatched"],
            "failed": warm_payload["failed"] + cold_payload["failed"],
        },
    }


@app.get("/dispatch/status")
async def dispatch_status(_: None = Depends(require_dashboard_auth)):
    """JSON: circuit breaker states, daily counts, KPI summary."""
    cb = CircuitBreaker()
    rl = DailyRateLimiter()
    payload = _build_dispatch_status_payload(circuit_breaker=cb, rate_limiter=rl)
    payload["mode"] = "warm_only" if is_warm_only_mode() else "mixed"
    return payload


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
