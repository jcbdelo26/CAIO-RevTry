"""End-to-end pipeline runner.

Sequence:
1. Check registry/pending_feedback/ (feedback_processor)
2. Recon → discover leads via Apollo
3. Enrichment → waterfall enrichment
4. Filter enrichment_score < 70 (GUARD-003)
5. Segmentation → authoritative ICP scoring
6. Filter DISQUALIFIED
7. Campaign Craft → draft emails
8. Validate output through Gates 1-3
9. Save drafts to dashboard storage
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

from models.schemas import (
    CampaignCraftOutput,
    EnrichmentOutput,
    EnrichmentRecord,
    ReconOutput,
    SegmentationOutput,
    ValidationResult,
)
from agents.recon_agent import run_recon
from agents.enrichment_agent import run_enrichment
from agents.segmentation_agent import segment_batch
from agents.campaign_craft_agent import craft_campaigns
from integrations.apollo_client import ApolloClient
from integrations.waterfall import WaterfallEnricher
from validators.gate1_validator import validate_gate1
from validators.gate2_validator import validate_gate2
from validators.gate3_validator import validate_gate3
from validators.guards import guard_003_enrichment_check
from dashboard.storage import save_draft
from pipeline.feedback_processor import process_pending_feedback
from utils.trace_logger import TraceLogger

logger = logging.getLogger(__name__)


async def run_pipeline(
    task_id: str,
    search_params: dict[str, Any],
    apollo: Optional[ApolloClient] = None,
    enricher: Optional[WaterfallEnricher] = None,
    is_cold: bool = True,
    max_recon_pages: int = 10,
) -> dict[str, Any]:
    """Run the full pipeline and return results summary."""
    trace = TraceLogger(task_id, "pipeline")

    # Step 1: Process pending feedback
    trace.log_event("feedback_check", "Processing pending feedback")
    feedback = process_pending_feedback()
    trace.log_event("feedback_result", {
        "pending": feedback.total_pending,
        "processed": feedback.processed,
        "blocked": feedback.contact_ids_blocked,
    })

    # Step 2: Recon
    trace.log_event("recon_start", "Starting Apollo discovery")
    if apollo is None:
        apollo = ApolloClient()

    recon_output: ReconOutput = await run_recon(
        task_id=f"{task_id}_recon",
        apollo=apollo,
        search_params=search_params,
        max_pages=max_recon_pages,
    )
    trace.log_tool_call("apollo_search_people")
    trace.log_event("recon_complete", {
        "records": recon_output.count,
        "excluded": recon_output.trace.records_excluded,
    })

    if recon_output.count == 0:
        trace.log_event("pipeline_stop", "No qualified leads found in recon")
        trace.write()
        return {"status": "no_leads", "recon_count": 0}

    # Step 3: Enrichment
    trace.log_event("enrichment_start", f"Enriching {recon_output.count} contacts")
    if enricher is None:
        enricher = WaterfallEnricher()

    enrichment_output: EnrichmentOutput = await run_enrichment(
        task_id=f"{task_id}_enrichment",
        records=recon_output.records,
        enricher=enricher,
    )
    trace.log_tool_call("waterfall_enrich")
    trace.log_event("enrichment_complete", {
        "ready": enrichment_output.trace.records_ready,
        "partial": enrichment_output.trace.records_partial,
        "minimal": enrichment_output.trace.records_minimal,
        "rejected": enrichment_output.trace.records_rejected,
    })

    # Step 4: GUARD-003 filter
    qualified_records: list[EnrichmentRecord] = []
    guard003_blocked = 0
    for record in enrichment_output.records:
        blocked, _ = guard_003_enrichment_check(record)
        if blocked:
            guard003_blocked += 1
        else:
            qualified_records.append(record)

    trace.log_event("guard003_filter", {
        "input": len(enrichment_output.records),
        "passed": len(qualified_records),
        "blocked": guard003_blocked,
    })

    if not qualified_records:
        trace.log_event("pipeline_stop", "All records blocked by GUARD-003")
        trace.write()
        return {"status": "all_blocked_guard003", "blocked": guard003_blocked}

    # Step 5: Segmentation
    trace.log_event("segmentation_start", f"Scoring {len(qualified_records)} contacts")
    segmentation_output: SegmentationOutput = segment_batch(
        task_id=f"{task_id}_segmentation",
        records=qualified_records,
    )
    trace.log_event("segmentation_complete", {
        "tier1": segmentation_output.trace.tier1_count,
        "tier2": segmentation_output.trace.tier2_count,
        "tier3": segmentation_output.trace.tier3_count,
        "disqualified": segmentation_output.trace.disqualified_count,
    })

    # Step 6: Filter DISQUALIFIED
    qualified_seg = [r for r in segmentation_output.records if r.icp_tier != "DISQUALIFIED"]
    if not qualified_seg:
        trace.log_event("pipeline_stop", "All records disqualified after segmentation")
        trace.write()
        return {"status": "all_disqualified", "dq_count": segmentation_output.trace.disqualified_count}

    # Step 7: Campaign Craft
    trace.log_event("campaign_craft_start", f"Drafting for {len(qualified_seg)} contacts")
    campaign_output: CampaignCraftOutput = craft_campaigns(
        task_id=f"{task_id}_campaign",
        records=qualified_seg,
        is_cold=is_cold,
    )
    trace.log_event("campaign_craft_complete", {"drafts": campaign_output.count})

    # Step 8: Validate through Gates 1-3
    gate1_result: ValidationResult = validate_gate1(campaign_output)
    gate2_result: ValidationResult = validate_gate2(campaign_output)
    gate3_result: ValidationResult = validate_gate3(campaign_output, segmentation_output)

    all_gates_passed = gate1_result.passed and gate2_result.passed and gate3_result.passed
    trace.log_event("validation", {
        "gate1": gate1_result.passed,
        "gate2": gate2_result.passed,
        "gate3": gate3_result.passed,
        "gate1_failures": gate1_result.failures,
        "gate2_failures": gate2_result.failures,
        "gate3_failures": gate3_result.failures,
    })

    # Step 9: Save drafts to dashboard
    saved_count = 0
    if all_gates_passed:
        for draft in campaign_output.drafts:
            save_draft(draft)
            saved_count += 1
        trace.log_event("drafts_saved", {"count": saved_count})
    else:
        trace.log_event("drafts_not_saved", "Validation failed — drafts not saved to dashboard")

    # Write trace log
    trace.write()

    return {
        "status": "complete" if all_gates_passed else "validation_failed",
        "recon_count": recon_output.count,
        "enriched_count": len(enrichment_output.records),
        "guard003_blocked": guard003_blocked,
        "segmented_count": len(segmentation_output.records),
        "disqualified_count": segmentation_output.trace.disqualified_count,
        "drafts_count": campaign_output.count,
        "drafts_saved": saved_count,
        "gates_passed": all_gates_passed,
        "gate1": gate1_result.model_dump(by_alias=True),
        "gate2": gate2_result.model_dump(by_alias=True),
        "gate3": gate3_result.model_dump(by_alias=True),
    }
