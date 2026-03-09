"""Warm follow-up generation orchestrator.

Pipeline:
1. Abort if the shared GHL circuit breaker is OPEN
2. Load follow-up candidates
3. Scan conversation history
4. Analyze eligible conversations
5. Filter actionable analyses
6. Draft warm follow-ups
7. Validate and persist valid drafts
8. Persist a daily briefing snapshot

This module never dispatches outreach. It only generates review-ready warm drafts.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.conversation_analyst_agent import AnalysisBatchResult, analyze_batch
from agents.followup_draft_agent import DraftBatchResult, draft_batch
from dashboard.followup_storage import save_followup_draft
from integrations.anthropic_client import AnthropicClient, MissingAnthropicApiKeyError
from integrations.ghl_client import MissingGhlCredentialsError
from models.schemas import ContactConversationSummary, ConversationAnalysis, DailyBriefing
from persistence.factory import get_storage_backend
from pipeline.circuit_breaker import CircuitBreaker
from scripts.ghl_conversation_scanner import (
    filter_eligible_summaries,
    load_candidates,
    scan_all_contacts,
)
from utils.business_time import current_business_date
from utils.trace_logger import TraceLogger
from validators.followup_gate2_validator import validate_followup_gate2
from validators.followup_gate3_validator import validate_followup_gate3

logger = logging.getLogger(__name__)

ESTIMATED_ANALYSIS_COST_USD = 0.001
ESTIMATED_DRAFT_COST_USD = 0.011
TERMINAL_STAGES = {"won", "lost"}


def _outputs_dir() -> Path:
    return Path(os.environ.get("OUTPUTS_DIR", "outputs"))


def _briefings_dir() -> Path:
    directory = _outputs_dir() / "briefings"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_briefing_date(reference_time: Optional[datetime] = None) -> str:
    return current_business_date(reference_time)


def _briefing_path(briefing_date: str) -> Path:
    return _briefings_dir() / f"{briefing_date}.json"


def _save_briefing(briefing: DailyBriefing) -> str:
    return get_storage_backend().save_daily_briefing(briefing)


def _count_by_attr(items: list[Any], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attr).value
        counts[value] = counts.get(value, 0) + 1
    return counts


def _estimated_cost_usd(eligible_count: int, actionable_count: int) -> float:
    return round(
        (eligible_count * ESTIMATED_ANALYSIS_COST_USD)
        + (actionable_count * ESTIMATED_DRAFT_COST_USD),
        4,
    )


def _actionable_analyses(analyses: list[ConversationAnalysis]) -> list[ConversationAnalysis]:
    return [analysis for analysis in analyses if analysis.stage.value not in TERMINAL_STAGES]


def _build_briefing(
    *,
    briefing_date: str,
    generated_at: str,
    summaries: list[ContactConversationSummary],
    analyses: list[ConversationAnalysis],
    actionable_analyses: list[ConversationAnalysis],
    saved_count: int,
    skipped_no_conversation: int,
    skipped_no_email: int,
    analysis_failed_count: int,
    draft_failed_count: int,
    estimated_cost_usd: float,
) -> DailyBriefing:
    urgency_counts = _count_by_attr(actionable_analyses, "urgency")
    trigger_counts = _count_by_attr(actionable_analyses, "trigger")

    return DailyBriefing(
        date=briefing_date,
        totalContactsScanned=len(summaries),
        contactsNeedingFollowup=len(actionable_analyses),
        contactsSkippedNoConversation=skipped_no_conversation,
        contactsSkippedNoEmail=skipped_no_email,
        hotCount=urgency_counts.get("hot", 0),
        warmCount=urgency_counts.get("warm", 0),
        coolingCount=urgency_counts.get("cooling", 0),
        noReplyCount=trigger_counts.get("no_reply", 0),
        awaitingResponseCount=trigger_counts.get("awaiting_our_response", 0),
        goneColdCount=trigger_counts.get("gone_cold", 0),
        draftsGenerated=saved_count,
        analysisFailedCount=analysis_failed_count,
        draftFailedCount=draft_failed_count,
        estimatedCostUsd=estimated_cost_usd,
        generatedAt=generated_at,
    )


async def run_followup_orchestrator(
    *,
    task_id: str = "warm-followup-generate",
    batch_size: int | None = None,
    scan_days: int | None = None,
    candidate_records: Optional[list[dict[str, Any]]] = None,
    force: bool = False,
    ghl=None,
    anthropic_client: AnthropicClient | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    reference_time: Optional[datetime] = None,
) -> dict[str, Any]:
    """Run the warm generate pipeline through briefing creation.

    Returns a summary dict with counts and status. This function never dispatches
    outreach and never mutates GHL.
    """
    trace = TraceLogger(task_id, "followup-orchestrator")
    reference_time = reference_time or datetime.now(timezone.utc)
    briefing_date = _resolve_briefing_date(reference_time)
    storage = get_storage_backend()
    circuit_breaker = circuit_breaker or CircuitBreaker()

    trace.log_event(
        "orchestrator_start",
        {"briefingDate": briefing_date, "force": force, "batchSize": batch_size, "scanDays": scan_days},
    )

    if circuit_breaker.is_open("ghl"):
        trace.log_event("orchestrator_abort", "GHL circuit breaker is OPEN")
        trace.write()
        return {
            "status": "circuit_open",
            "briefing_date": briefing_date,
            "briefing_path": None,
            "errors": ["Circuit breaker OPEN for ghl"],
        }

    existing_briefing = storage.get_daily_briefing(briefing_date)
    if existing_briefing and not force:
        trace.log_event("orchestrator_skip", "Briefing already exists for this business date")
        trace.write()
        return {
            "status": "already_generated",
            "briefing_date": briefing_date,
            "briefing_path": f"briefing://{briefing_date}",
            "errors": [],
        }

    candidates = candidate_records if candidate_records is not None else load_candidates(batch_size=batch_size)
    trace.log_event("candidates_loaded", {"count": len(candidates)})

    if not candidates:
        briefing = _build_briefing(
            briefing_date=briefing_date,
            generated_at=reference_time.isoformat(),
            summaries=[],
            analyses=[],
            actionable_analyses=[],
            saved_count=0,
            skipped_no_conversation=0,
            skipped_no_email=0,
            analysis_failed_count=0,
            draft_failed_count=0,
            estimated_cost_usd=0.0,
        )
        saved_briefing = _save_briefing(briefing)
        trace.log_event("briefing_saved", {"path": str(saved_briefing), "draftsGenerated": 0})
        result = {
            "status": "no_candidates",
            "briefing_date": briefing_date,
            "briefing_path": str(saved_briefing),
            "candidates_loaded": 0,
            "scanned": 0,
            "eligible": 0,
            "skipped_no_conversation": 0,
            "skipped_no_email": 0,
            "analyzed": 0,
            "analysis_failed": 0,
            "actionable": 0,
            "drafted": 0,
            "draft_failed": 0,
            "validation_failed": 0,
            "saved": 0,
            "estimated_cost_usd": 0.0,
            "errors": [],
        }
        trace.log_event("orchestrator_complete", result)
        trace.write()
        return result

    if anthropic_client is None:
        try:
            anthropic_client = AnthropicClient()
        except MissingAnthropicApiKeyError as exc:
            trace.log_error(str(exc))
            trace.write()
            return {
                "status": "blocked_missing_anthropic_api_key",
                "briefing_date": briefing_date,
                "briefing_path": None,
                "errors": [str(exc)],
            }
        own_client = True
    else:
        own_client = False

    summaries: list[ContactConversationSummary] = []
    analysis_result = AnalysisBatchResult()
    draft_result = DraftBatchResult()
    actionable: list[ConversationAnalysis] = []
    validation_failed = 0
    validation_errors: list[str] = []
    saved_count = 0
    generation_run_id = f"{task_id}-{reference_time.strftime('%Y%m%d%H%M%S')}"

    try:
        try:
            summaries = await scan_all_contacts(candidates, ghl=ghl, scan_days=scan_days)
        except MissingGhlCredentialsError as exc:
            trace.log_error(str(exc))
            return {
                "status": "blocked_missing_ghl_credentials",
                "briefing_date": briefing_date,
                "briefing_path": None,
                "errors": [str(exc)],
            }
        eligible_summaries, skipped_no_conversation, skipped_no_email = filter_eligible_summaries(summaries)
        trace.log_event(
            "conversation_scan_complete",
            {
                "candidates": len(candidates),
                "summaries": len(summaries),
                "eligible": len(eligible_summaries),
                "skippedNoConversation": skipped_no_conversation,
                "skippedNoEmail": skipped_no_email,
            },
        )
        trace.log_tool_call("ghl_conversation_scan")

        analysis_result = await analyze_batch(
            summaries,
            client=anthropic_client,
            reference_time=reference_time,
        )
        trace.log_event(
            "analysis_complete",
            {
                "analyzed": len(analysis_result.analyses),
                "failed": analysis_result.failed,
                "skipped": analysis_result.skipped,
            },
        )
        trace.log_tool_call("anthropic_haiku_analysis")

        actionable = _actionable_analyses(analysis_result.analyses)
        trace.log_event(
            "actionable_filter",
            {
                "input": len(analysis_result.analyses),
                "actionable": len(actionable),
                "blockedTerminalStage": len(analysis_result.analyses) - len(actionable),
            },
        )

        if actionable:
            draft_result = await draft_batch(
                actionable,
                summaries,
                client=anthropic_client,
                business_date=briefing_date,
                generation_run_id=generation_run_id,
            )
            trace.log_event(
                "draft_generation_complete",
                {
                    "drafts": len(draft_result.drafts),
                    "failed": draft_result.failed,
                },
            )
            trace.log_tool_call("anthropic_sonnet_drafting")

            analyses_by_contact = {analysis.contact_id: analysis for analysis in actionable}
            summaries_by_contact = {summary.contact_id: summary for summary in summaries}

            for draft in draft_result.drafts:
                gate2 = validate_followup_gate2([draft])
                gate3 = validate_followup_gate3(
                    [draft],
                    analyses_by_contact,
                    summaries_by_contact,
                )

                if gate2.passed and gate3.passed:
                    save_followup_draft(draft)
                    saved_count += 1
                    continue

                validation_failed += 1
                validation_errors.extend(gate2.failures)
                validation_errors.extend(gate3.failures)

            trace.log_event(
                "draft_validation_complete",
                {
                    "saved": saved_count,
                    "validationFailed": validation_failed,
                },
            )

        estimated_cost_usd = _estimated_cost_usd(len(eligible_summaries), len(actionable))
        briefing = _build_briefing(
            briefing_date=briefing_date,
            generated_at=reference_time.isoformat(),
            summaries=summaries,
            analyses=analysis_result.analyses,
            actionable_analyses=actionable,
            saved_count=saved_count,
            skipped_no_conversation=analysis_result.skipped_no_conversation,
            skipped_no_email=analysis_result.skipped_no_email,
            analysis_failed_count=analysis_result.failed,
            draft_failed_count=draft_result.failed + validation_failed,
            estimated_cost_usd=estimated_cost_usd,
        )
        saved_briefing = _save_briefing(briefing)
        trace.log_event(
            "briefing_saved",
            {"path": str(saved_briefing), "draftsGenerated": briefing.drafts_generated},
        )

        if not candidates:
            status = "no_candidates"
        elif not actionable:
            status = "no_actionable_analyses"
        elif saved_count == 0:
            status = "no_valid_drafts"
        else:
            status = "complete"

        result = {
            "status": status,
            "briefing_date": briefing_date,
            "briefing_path": str(saved_briefing),
            "candidates_loaded": len(candidates),
            "scanned": len(summaries),
            "eligible": len(eligible_summaries),
            "skipped_no_conversation": analysis_result.skipped_no_conversation,
            "skipped_no_email": analysis_result.skipped_no_email,
            "analyzed": len(analysis_result.analyses),
            "analysis_failed": analysis_result.failed,
            "actionable": len(actionable),
            "drafted": len(draft_result.drafts),
            "draft_failed": draft_result.failed + validation_failed,
            "validation_failed": validation_failed,
            "saved": saved_count,
            "estimated_cost_usd": estimated_cost_usd,
            "errors": analysis_result.errors + draft_result.errors + validation_errors,
        }
        trace.log_event("orchestrator_complete", result)
        return result
    finally:
        if own_client:
            await anthropic_client.close()
        trace.write()
