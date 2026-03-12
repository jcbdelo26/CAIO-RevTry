"""GHL Pipeline Runner — Feed enriched GHL contacts through the campaign pipeline.

Mid-pipeline entry point for contacts already enriched via ghl_enrich.py.
Skips recon (Apollo search) and re-enriches from whitelist data to produce
fresh EnrichmentRecords, then runs:

  GUARD-003 → Segmentation → DQ Filter → Campaign Craft → Gates 1-3 → Dashboard

Usage:
  python -m scripts.ghl_pipeline                   # Full run
  python -m scripts.ghl_pipeline --dry-run         # Skip save_draft, show results
  python -m scripts.ghl_pipeline --limit 5         # Process first 5 candidates
  python -m scripts.ghl_pipeline --min-score 90    # Only READY contacts (default: 70)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.stdout.reconfigure(encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(override=True)

from agents.campaign_craft_agent import craft_campaigns
from agents.segmentation_agent import segment_batch
from dashboard.storage import save_draft
from integrations.waterfall import WaterfallEnricher
from models.schemas import EnrichmentRecord
from scripts.ghl_enrich import load_whitelist
from validators.gate1_validator import validate_gate1
from validators.gate2_validator import validate_gate2
from validators.gate3_validator import validate_gate3
from validators.guards import guard_003_enrichment_check


async def run_ghl_pipeline(
    dry_run: bool = False,
    limit: int | None = None,
    min_score: int = 70,
    enricher: WaterfallEnricher | None = None,
) -> dict[str, Any]:
    """Run the campaign pipeline on enriched GHL follow-up contacts."""
    task_id = f"ghl_pipeline_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    print("=" * 60)
    print("GHL PIPELINE RUNNER")
    print(f"Mode: {'DRY RUN' if dry_run else 'FULL RUN'}")
    print(f"Min enrichment score: {min_score}")
    print("=" * 60)

    # ── Step 1: Load whitelist ─────────────────────────────────────────────
    candidates = load_whitelist()
    print(f"\nWhitelist loaded: {len(candidates)} candidates")

    if limit:
        candidates = candidates[:limit]
        print(f"Limiting to first {limit} candidates")

    # ── Step 2: Enrich → EnrichmentRecord ──────────────────────────────────
    print(f"\nEnriching {len(candidates)} contacts via Apollo...")
    own_enricher = enricher is None
    if own_enricher:
        enricher = WaterfallEnricher()

    records: list[EnrichmentRecord] = []
    for i, c in enumerate(candidates):
        try:
            record = await enricher.enrich(
                contact_id=c["ghl_contact_id"],
                email=c.get("email"),
                first_name=c.get("first_name") or None,
                last_name=c.get("last_name") or None,
                company_name=c.get("company_name") or None,
            )
            records.append(record)
            if (i + 1) % 10 == 0:
                print(f"  Enriched {i + 1}/{len(candidates)}...")
        except Exception as e:
            print(f"  FAILED {c.get('email', 'unknown')}: {e}")

    if own_enricher:
        await enricher.close()

    print(f"  Total enrichment records: {len(records)}")

    # ── Step 3: GUARD-003 filter ───────────────────────────────────────────
    print(f"\nApplying GUARD-003 (min score: {min_score})...")
    qualified: list[EnrichmentRecord] = []
    guard003_blocked = 0
    for record in records:
        blocked, reason = guard_003_enrichment_check(record, threshold=min_score)
        if blocked:
            guard003_blocked += 1
        else:
            qualified.append(record)

    print(f"  Passed GUARD-003: {len(qualified)}")
    print(f"  Blocked: {guard003_blocked}")

    if not qualified:
        print("\nAll records blocked by GUARD-003. Pipeline stopped.")
        return {"status": "all_blocked_guard003", "blocked": guard003_blocked}

    # ── Step 4: Segmentation ───────────────────────────────────────────────
    print(f"\nRunning segmentation on {len(qualified)} contacts...")
    seg_output = segment_batch(task_id=f"{task_id}_seg", records=qualified)

    t1 = seg_output.trace.tier1_count
    t2 = seg_output.trace.tier2_count
    t3 = seg_output.trace.tier3_count
    dq = seg_output.trace.disqualified_count
    print(f"  Tier 1: {t1} | Tier 2: {t2} | Tier 3: {t3} | DQ: {dq}")

    # ── Step 5: Filter DISQUALIFIED ────────────────────────────────────────
    qualified_seg = [r for r in seg_output.records if r.icp_tier != "DISQUALIFIED"]
    print(f"  After DQ filter: {len(qualified_seg)} contacts")

    if not qualified_seg:
        print("\nAll records disqualified after segmentation. Pipeline stopped.")
        return {"status": "all_disqualified", "dq_count": dq}

    # ── Step 6: Campaign Craft ─────────────────────────────────────────────
    print(f"\nCrafting campaigns for {len(qualified_seg)} contacts...")
    campaign_output = craft_campaigns(
        task_id=f"{task_id}_campaign",
        records=qualified_seg,
        is_cold=False,  # GHL contacts are warm — route to channel="ghl"
    )
    print(f"  Drafts generated: {campaign_output.count}")

    # ── Step 7: Gates 1-3 ─────────────────────────────────────────────────
    print("\nRunning validation gates...")
    gate1 = validate_gate1(campaign_output)
    gate2 = validate_gate2(campaign_output)
    gate3 = validate_gate3(campaign_output, seg_output)

    print(f"  Gate 1: {'PASS' if gate1.passed else 'FAIL'} ({gate1.checks_passed}/{gate1.checks_run})")
    if gate1.failures:
        for f in gate1.failures[:3]:
            print(f"    - {f}")
    print(f"  Gate 2: {'PASS' if gate2.passed else 'FAIL'} ({gate2.checks_passed}/{gate2.checks_run})")
    if gate2.failures:
        for f in gate2.failures[:3]:
            print(f"    - {f}")
    print(f"  Gate 3: {'PASS' if gate3.passed else 'FAIL'} ({gate3.checks_passed}/{gate3.checks_run})")
    if gate3.failures:
        for f in gate3.failures[:3]:
            print(f"    - {f}")

    all_gates_passed = gate1.passed and gate2.passed and gate3.passed

    # ── Step 8: Save drafts ────────────────────────────────────────────────
    saved_count = 0
    if all_gates_passed and not dry_run:
        print(f"\nSaving {campaign_output.count} drafts to dashboard...")
        for draft in campaign_output.drafts:
            save_draft(draft)
            saved_count += 1
        print(f"  Saved: {saved_count} drafts")
    elif dry_run:
        print(f"\nDRY RUN — {campaign_output.count} drafts would be saved (skipped)")
    else:
        print(f"\nValidation FAILED — drafts NOT saved")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("PIPELINE SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Candidates:     {len(candidates)}")
    print(f"  Enriched:       {len(records)}")
    print(f"  GUARD-003 pass: {len(qualified)} (blocked: {guard003_blocked})")
    print(f"  Segmented:      T1={t1} T2={t2} T3={t3} DQ={dq}")
    print(f"  Drafts:         {campaign_output.count}")
    print(f"  Gates:          {'ALL PASS' if all_gates_passed else 'FAILED'}")
    print(f"  Saved:          {saved_count}")

    return {
        "status": "complete" if all_gates_passed else "validation_failed",
        "candidates": len(candidates),
        "enriched": len(records),
        "guard003_blocked": guard003_blocked,
        "guard003_passed": len(qualified),
        "tier1": t1,
        "tier2": t2,
        "tier3": t3,
        "disqualified": dq,
        "drafts": campaign_output.count,
        "gates_passed": all_gates_passed,
        "saved": saved_count,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Run GHL contacts through campaign pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip saving drafts to dashboard")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N candidates")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum enrichment score (default: 70)")
    args = parser.parse_args()

    asyncio.run(run_ghl_pipeline(
        dry_run=args.dry_run,
        limit=args.limit,
        min_score=args.min_score,
    ))


if __name__ == "__main__":
    main()
