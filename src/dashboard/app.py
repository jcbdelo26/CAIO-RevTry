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
- GET /api/cron/warm-pipeline — Vercel Cron Job trigger (CRON_SECRET auth)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=True)

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
    save_followup_draft,
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
from persistence.factory import get_storage_backend, get_storage_backend_name, validate_storage_configuration
from scripts.ghl_conversation_scanner import select_primary_thread
from validators.followup_gate2_validator import validate_followup_gate2
from validators.followup_gate3_validator import validate_followup_gate3

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


def _get_followup_queue_item_by_contact(contact_id: str, date: Optional[str] = None) -> Optional[dict]:
    for item in load_followup_queue(date=date):
        if item.get("contactId") == contact_id:
            return item
    return None


def _get_followup_queue_item_by_draft(draft_id: str, date: Optional[str] = None) -> Optional[dict]:
    for item in load_followup_queue(date=date):
        if item.get("draftId") == draft_id:
            return item
    return None


def _get_latest_followup_draft_for_contact(contact_id: str, date: Optional[str] = None):
    drafts = list_followup_drafts(business_date=date, latest_only=False)
    for draft in drafts:
        if draft.contact_id == contact_id:
            return draft
    return None


def _select_display_thread(summary, source_conversation_id: Optional[str]):
    if summary and source_conversation_id:
        for candidate in summary.threads:
            if candidate.conversation_id == source_conversation_id:
                return candidate
    if summary:
        return select_primary_thread(summary)
    return None


def _build_followup_detail_context(
    *,
    contact_id: str,
    date: Optional[str] = None,
    draft=None,
) -> dict:
    queue_item = _get_followup_queue_item_by_contact(contact_id, date=date)
    conversation = load_contact_conversation(contact_id)
    draft = draft or (queue_item["draft"] if queue_item else None) or _get_latest_followup_draft_for_contact(contact_id, date=date)
    analysis = queue_item["analysis"] if queue_item else get_storage_backend().get_conversation_analysis(contact_id)
    summary = queue_item["summary"] if queue_item else conversation
    source_conversation_id = None
    if draft:
        source_conversation_id = draft.source_conversation_id
    elif analysis:
        source_conversation_id = analysis.source_conversation_id
    display_thread = _select_display_thread(summary, source_conversation_id)
    return {
        "queue_item": queue_item,
        "draft": draft,
        "analysis": analysis,
        "summary": summary,
        "conversation": conversation,
        "display_thread": display_thread,
        "selected_date": date or (queue_item["businessDate"] if queue_item else (draft.business_date if draft else None)),
    }


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


def _render_error_state(
    request: Request,
    *,
    title: str,
    message: str,
    back_href: str,
    back_label: str,
    status_code: int = 503,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "error_state.html",
        {
            "title": title,
            "message": message,
            "back_href": back_href,
            "back_label": back_label,
        },
        status_code=status_code,
    )


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
    # Compute live draft status counts from fresh queue data
    draft_status_counts = {"pending": 0, "approved": 0, "rejected": 0, "dispatched": 0, "send_failed": 0}
    for item in queue:
        status = item.get("status")
        if status is not None:
            draft_status_counts[status.value.lower()] += 1

    return templates.TemplateResponse(
        request,
        "briefing.html",
        {
            "briefing": briefing,
            "queue": queue,
            "selected_date": briefing.date,
            "live_draft_count": len(queue),
            "draft_status_counts": draft_status_counts,
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


@app.get("/followups/contact/{contact_id}", response_class=HTMLResponse)
async def followup_contact_detail_view(
    request: Request,
    contact_id: str,
    date: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    try:
        context = _build_followup_detail_context(contact_id=contact_id, date=date)
    except Exception:
        logger.exception("Failed to load routed follow-up detail")
        return _render_error_state(
            request,
            title="Follow-Up Unavailable",
            message="The routed lead could not be loaded right now.",
            back_href="/followups",
            back_label="Back to Follow-Ups",
        )

    if not context["queue_item"] and not context["summary"] and not context["draft"]:
        raise HTTPException(status_code=404, detail="Follow-up lead not found")

    return templates.TemplateResponse(
        request,
        "followup_detail.html",
        context,
    )


@app.post("/followups/batch/approve")
async def batch_approve_followups(
    draft_ids: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    ids = [draft_id.strip() for draft_id in draft_ids.split(",") if draft_id.strip()]
    dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")
    for draft_id in ids:
        draft = approve_followup_draft(draft_id)
        if draft:
            try:
                from pipeline.followup_dispatcher import dispatch_single_draft
                await dispatch_single_draft(draft, dry_run=dry_run)
            except Exception:
                logger.exception("Immediate dispatch failed for %s — cron will retry", draft_id)
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
    refresh: bool = Form(False),
    batch_size: int | None = Form(None),
    scan_days: int | None = Form(None),
    _: None = Depends(require_dashboard_auth),
):
    batch_size = min(batch_size, 500) if batch_size else None
    scan_days = min(scan_days, 180) if scan_days else None
    try:
        if refresh:
            from scripts.ghl_conversation_scanner import refresh_candidates
            await refresh_candidates(batch_size=batch_size or 100)

        result = await run_followup_orchestrator(
            task_id="warm-followup-manual",
            force=force,
            batch_size=batch_size,
            scan_days=scan_days,
        )
    except Exception:
        logger.exception("Failed to generate follow-ups")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "briefing_date": None,
                "briefing_path": None,
                "saved": 0,
                "errors": ["Warm pipeline unavailable"],
            },
        )

    status = result.get("status")
    if status in {"blocked_missing_anthropic_api_key", "blocked_missing_ghl_credentials", "circuit_open"}:
        return JSONResponse(status_code=503, content=result)

    return JSONResponse(status_code=200, content=result)


def _verify_cron_secret(request: Request) -> None:
    """Validate the Vercel CRON_SECRET Authorization header."""
    secret = os.environ.get("CRON_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _send_slack_alert(message: str) -> None:
    """Best-effort Slack webhook alert. Silently swallows all errors."""
    webhook_url = os.environ.get("ALERT_SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as hx:
            await hx.post(webhook_url, json={"text": message})
    except Exception:
        logger.warning("Slack alert failed (non-blocking)", exc_info=True)


@app.get("/api/cron/warm-pipeline")
async def cron_warm_pipeline(request: Request):
    """Vercel Cron Job endpoint — triggers daily warm follow-up pipeline.

    Phase 1: Run generation orchestrator.
    Phase 2: Auto-dispatch any APPROVED drafts immediately.
    Secured via CRON_SECRET Bearer token (set as Vercel env var).
    Runs at 12:00 UTC (6:00 AM CT) daily via vercel.json crons config.
    """
    try:
        _verify_cron_secret(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            await _send_slack_alert(
                ":lock: *RevTry \u2014 Unauthorized Cron Request*\n"
                f"\u2022 Path: {request.url.path}\n"
                f"\u2022 IP: {request.client.host if request.client else 'unknown'}\n"
                f"\u2022 Auth header present: {'yes' if request.headers.get('authorization') else 'no'}\n"
                "\u2022 Check: CRON_SECRET may be mis-configured in Vercel env vars"
            )
        raise

    dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")

    try:
        orchestrator_result = await run_followup_orchestrator(
            task_id="warm-followup-cron",
            force=False,
        )
    except Exception:
        logger.exception("Cron warm pipeline failed")
        return JSONResponse(status_code=500, content={"status": "error", "errors": ["Pipeline execution failed"]})

    # Alert when ALL draft generation failed (partial failures are acceptable noise)
    _draft_failed = orchestrator_result.get("draft_failed", 0)
    _actionable = orchestrator_result.get("actionable", 0)
    if _draft_failed > 0 and _actionable > 0 and _draft_failed >= _actionable:
        await _send_slack_alert(
            ":warning: *RevTry \u2014 Draft Generation Failure* "
            f"({orchestrator_result.get('briefing_date')})\n"
            f"\u2022 Failed: {_draft_failed} | Drafted: {orchestrator_result.get('drafted', 0)} "
            f"| Actionable: {_actionable}\n"
            "\u2022 Likely cause: Anthropic API overloaded (529). "
            "Fix: re-run with force=True or wait for tomorrow's cron.\n"
            "\u2022 Review: <https://caio-rev-try.vercel.app/briefing|Briefing Dashboard>"
        )

    dispatch_payload = None
    try:
        cb = CircuitBreaker()
        rl = DailyRateLimiter()
        warm = await dispatch_approved_followups(
            rate_limiter=rl, circuit_breaker=cb, dry_run=dry_run,
        )
        dispatch_payload = {
            "dispatched": warm.dispatched,
            "skippedDedup": warm.skipped_dedup,
            "skippedRateLimit": warm.skipped_rate_limit,
            "skippedCircuitBreaker": warm.skipped_circuit_breaker,
            "failed": warm.failed,
            "errors": warm.errors,
        }
    except Exception:
        logger.exception("Cron auto-dispatch failed")
        dispatch_payload = {"status": "error", "errors": ["Auto-dispatch failed"]}
        await _send_slack_alert(
            ":rotating_light: RevTry - Dispatch Crashed: Auto-dispatch raised an"
            " unhandled exception. 0 sends completed."
            " Review: https://caio-rev-try.vercel.app/dispatch"
        )
    # Alert on any per-contact dispatch failure (each failed send = a contact missed)
    _dispatch_failed = (dispatch_payload or {}).get("failed", 0)
    if _dispatch_failed > 0:
        _dispatch_errors = (dispatch_payload or {}).get("errors") or []
        await _send_slack_alert(
            ":rotating_light: *RevTry \u2014 Dispatch Failure* "
            f"({orchestrator_result.get('briefing_date')})\n"
            f"\u2022 Failed: {_dispatch_failed} | "
            f"Dispatched: {(dispatch_payload or {}).get('dispatched', 0)}\n"
            + (f"\u2022 Errors: {'; '.join(str(e) for e in _dispatch_errors[:2])}\n" if _dispatch_errors else "")
            + "\u2022 Review: <https://caio-rev-try.vercel.app/dispatch|Dispatch Dashboard>"
        )

    return JSONResponse(
        status_code=200,
        content={**orchestrator_result, "dispatch": dispatch_payload},
    )


@app.get("/api/cron/dispatch")
async def cron_dispatch(request: Request):
    """Dispatch-only cron endpoint — sends APPROVED warm drafts on demand.

    Useful for immediate dispatch after manual approval without waiting
    for the daily 6 AM CT pipeline run. Secured via CRON_SECRET Bearer token.
    """
    _verify_cron_secret(request)
    dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")

    try:
        cb = CircuitBreaker()
        rl = DailyRateLimiter()
        warm = await dispatch_approved_followups(
            rate_limiter=rl, circuit_breaker=cb, dry_run=dry_run,
        )
    except MissingGhlCredentialsError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "blocked_missing_ghl_credentials", "errors": [str(exc)]},
        )
    except Exception:
        logger.exception("Cron dispatch failed")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "errors": ["Dispatch failed"]},
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "dispatched": warm.dispatched,
            "skippedDedup": warm.skipped_dedup,
            "skippedRateLimit": warm.skipped_rate_limit,
            "skippedCircuitBreaker": warm.skipped_circuit_breaker,
            "failed": warm.failed,
            "errors": warm.errors,
        },
    )


@app.get("/followups/{draft_id}", response_class=HTMLResponse)
async def followup_detail_view(
    request: Request,
    draft_id: str,
    date: Optional[str] = None,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    try:
        draft = get_followup_draft(draft_id)
    except Exception:
        logger.exception("Failed to load follow-up detail")
        return _render_error_state(
            request,
            title="Follow-Up Unavailable",
            message="The follow-up draft could not be loaded right now.",
            back_href="/followups",
            back_label="Back to Follow-Ups",
        )
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    target_date = date or draft.business_date
    return RedirectResponse(
        url=f"/followups/contact/{draft.contact_id}?date={target_date}",
        status_code=307,
    )


@app.post("/followups/{draft_id}/approve")
async def approve_followup_endpoint(
    draft_id: str,
    _: None = Depends(require_dashboard_auth),
):
    draft = approve_followup_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")

    # Send-on-approve: dispatch immediately through the full safety chain
    dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")
    try:
        from pipeline.followup_dispatcher import dispatch_single_draft
        await dispatch_single_draft(draft, dry_run=dry_run)
    except Exception:
        logger.exception("Immediate dispatch failed for %s — cron will retry", draft_id)

    return RedirectResponse(url=f"/followups/contact/{draft.contact_id}?date={draft.business_date}", status_code=303)


@app.post("/followups/{draft_id}/reject")
async def reject_followup_endpoint(
    draft_id: str,
    reason: str = Form(""),
    _: None = Depends(require_dashboard_auth),
):
    draft = reject_followup_draft(draft_id, reason=reason)
    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")
    return RedirectResponse(url=f"/followups/contact/{draft.contact_id}?date={draft.business_date}", status_code=303)


@app.post("/followups/{draft_id}/edit")
async def edit_followup_endpoint(
    request: Request,
    draft_id: str,
    subject: str = Form(""),
    body: str = Form(""),
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    try:
        draft = get_followup_draft(draft_id)
    except Exception:
        logger.exception("Failed to load follow-up draft for edit")
        return _render_error_state(
            request,
            title="Follow-Up Unavailable",
            message="The follow-up draft could not be loaded right now.",
            back_href="/followups",
            back_label="Back to Follow-Ups",
        )

    if not draft:
        raise HTTPException(status_code=404, detail="Follow-up draft not found")

    if draft.status == DraftApprovalStatus.DISPATCHED:
        context = _build_followup_detail_context(contact_id=draft.contact_id, date=draft.business_date, draft=draft)
        context["edit_errors"] = ["This draft has already been dispatched and can no longer be edited."]
        context["edit_subject"] = draft.subject
        context["edit_body"] = draft.body
        context["edit_disabled_message"] = "This draft has already been dispatched and can no longer be edited."
        return templates.TemplateResponse(request, "followup_detail.html", context, status_code=409)

    try:
        context = _build_followup_detail_context(contact_id=draft.contact_id, date=draft.business_date, draft=draft)
    except Exception:
        logger.exception("Failed to load follow-up detail for edit")
        return _render_error_state(
            request,
            title="Follow-Up Unavailable",
            message="The routed lead could not be loaded right now.",
            back_href="/followups",
            back_label="Back to Follow-Ups",
        )

    updated = draft.model_copy(deep=True)
    updated.subject = subject.strip()
    updated.body = body.strip().replace("\r\n", "\n")

    failures: list[str] = []
    if not updated.subject:
        failures.append("Subject is required.")
    if not updated.body:
        failures.append("Body is required.")

    try:
        gate2 = validate_followup_gate2([updated])
        if not gate2.passed:
            failures.extend(gate2.failures)

        analyses = {}
        summaries = {}
        if context["analysis"] is not None:
            analyses[updated.contact_id] = context["analysis"]
        if context["summary"] is not None:
            summaries[updated.contact_id] = context["summary"]
        gate3 = validate_followup_gate3([updated], analyses, summaries or None)
        if not gate3.passed:
            failures.extend(gate3.failures)
    except FileNotFoundError:
        logger.warning("Vault files missing — skipping Gate 2/3 validation for edit")

    if failures:
        context["edit_errors"] = failures
        context["edit_subject"] = subject
        context["edit_body"] = body
        return templates.TemplateResponse(request, "followup_detail.html", context, status_code=422)

    if updated.status in {DraftApprovalStatus.APPROVED, DraftApprovalStatus.REJECTED, DraftApprovalStatus.SEND_FAILED}:
        updated.status = DraftApprovalStatus.PENDING
        updated.approved_at = None
        updated.rejected_at = None
        updated.rejection_reason = None
        updated.send_failed_at = None
        updated.dispatch_error = None

    updated.edited_at = datetime.now(timezone.utc).isoformat()
    try:
        save_followup_draft(updated)
    except Exception:
        logger.exception("Failed to save follow-up draft")
        context["edit_errors"] = ["The draft could not be saved right now. Please try again."]
        context["edit_subject"] = subject
        context["edit_body"] = body
        return templates.TemplateResponse(request, "followup_detail.html", context, status_code=503)
    return RedirectResponse(url=f"/followups/contact/{updated.contact_id}?date={updated.business_date}", status_code=303)


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
    result = {
        "status": "ok",
        "mode": "warm_only" if is_warm_only_mode() else "mixed",
        "storageBackend": get_storage_backend_name(),
    }
    if result["storageBackend"] == "postgres":
        try:
            backend = get_storage_backend()
            with backend._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            result["db"] = "connected"
        except Exception as exc:
            logger.exception("Healthz Postgres probe failed")
            result["status"] = "degraded"
            result["db"] = "error"
            result["detail"] = str(exc)
    return result


# ── Dispatch Endpoints ─────────────────────────────────────────────────────────


@app.get("/dispatch", response_class=HTMLResponse)
async def dispatch_view(
    request: Request,
    _: None = Depends(require_dashboard_auth),
) -> HTMLResponse:
    """Show unified warm/cold dispatch queues and recent dispatch history."""
    warm_only = is_warm_only_mode()
    dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")
    warm_queue = []
    warm_dispatched = []
    cold_queue = []
    cold_dispatched = []
    cb_states = {}
    daily_counts = {}
    daily_limit = 0
    snapshot = None
    load_error = None

    try:
        warm_drafts = list_followup_drafts(latest_only=False)
        warm_queue = [draft for draft in warm_drafts if draft.status == DraftApprovalStatus.APPROVED]
        warm_dispatched = [
            draft for draft in warm_drafts if draft.status == DraftApprovalStatus.DISPATCHED
        ]
        if not warm_only:
            all_drafts = list_drafts()
            cold_queue = [d for d in all_drafts if d.status == DraftApprovalStatus.APPROVED]
            cold_dispatched = [d for d in all_drafts if d.status == DraftApprovalStatus.DISPATCHED]
        cb = CircuitBreaker()
        rl = DailyRateLimiter()
        cb_states = cb.get_all_states()
        daily_counts = rl.get_counts()
        daily_limit = rl.limit
        snapshot = KPITracker(circuit_breaker=cb).get_latest_kpi()
    except Exception:
        logger.exception("Failed to load dispatch data")
        load_error = "Dispatch data unavailable"

    return templates.TemplateResponse(
        request,
        "dispatch.html",
        {
            "warm_queue": warm_queue,
            "warm_dispatched": warm_dispatched,
            "cold_queue": cold_queue,
            "cold_dispatched": cold_dispatched,
            "warm_only_mode": warm_only,
            "cb_states": cb_states,
            "daily_counts": daily_counts,
            "daily_limit": daily_limit,
            "kpi": snapshot,
            "load_error": load_error,
            "dry_run": dry_run,
            "ghl_contact_base": (
                f"https://app.gohighlevel.com/v2/location/"
                f"{os.environ.get('GHL_LOCATION_ID', '')}/contacts/detail"
                if os.environ.get("GHL_LOCATION_ID") else ""
            ),
        },
    )


@app.post("/dispatch/run")
async def dispatch_run(_: None = Depends(require_dashboard_auth)):
    """Trigger a unified warm-first dispatch cycle."""
    try:
        cb = CircuitBreaker()
        rl = DailyRateLimiter()
        warm_only = is_warm_only_mode()
        dry_run = os.environ.get("DISPATCH_DRY_RUN", "").lower() in ("true", "1", "yes")
        warm = await dispatch_approved_followups(
            rate_limiter=rl,
            circuit_breaker=cb,
            dry_run=dry_run,
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
    except Exception:
        logger.exception("Dispatch run failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "warm": {
                    "dispatched": 0,
                    "skippedDedup": 0,
                    "skippedRateLimit": 0,
                    "skippedCircuitBreaker": 0,
                    "failed": 0,
                    "errors": [],
                },
                "cold": {
                    "dispatched": 0,
                    "skippedDedup": 0,
                    "skippedRateLimit": 0,
                    "skippedCircuitBreaker": 0,
                    "skippedTier": 0,
                    "skippedDeferredChannel": 0,
                    "failed": 0,
                    "errors": [],
                },
                "totals": {"dispatched": 0, "failed": 0},
                "errors": ["Dispatch run failed"],
            },
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
    try:
        cb = CircuitBreaker()
        rl = DailyRateLimiter()
        payload = _build_dispatch_status_payload(circuit_breaker=cb, rate_limiter=rl)
        payload["mode"] = "warm_only" if is_warm_only_mode() else "mixed"
        return payload
    except Exception:
        logger.exception("Dispatch status unavailable")
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "mode": "warm_only" if is_warm_only_mode() else "mixed",
                "errors": ["Dispatch status unavailable"],
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
