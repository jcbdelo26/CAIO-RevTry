"""GHL Follow-Up Enrichment — Apollo-only, whitelist-gated.

HARDBLOCKS:
1. Only processes contacts listed in outputs/ghl_followup_candidates.json
2. Only calls Apollo /people/match (enrichment) — never /mixed_people/api_search (recon)
3. Only produces enrichment records — never generates drafts or campaigns
4. Verifies email identity before accepting Apollo match
5. Dry-run by default — pass --commit to write enrichment data back to GHL

Usage:
  python -m scripts.ghl_enrich              # Dry run — enrich + report only
  python -m scripts.ghl_enrich --commit     # Enrich + write back to GHL
  python -m scripts.ghl_enrich --limit 5    # Process only first 5 candidates
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from integrations.ghl_client import GHLClient
from integrations.waterfall import WaterfallEnricher
from models.schemas import EnrichmentGrade, EnrichmentRecord


# ── HARDBLOCK-1: Whitelist Gate ────────────────────────────────────────────────


def load_whitelist(outputs_dir: str | None = None) -> list[dict]:
    """Load the enrichment whitelist. Only contacts in this file will be processed."""
    base = Path(outputs_dir) if outputs_dir else Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    path = base / "ghl_followup_candidates.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Whitelist not found at {path}. Run ghl_audit.py first to generate candidates."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Whitelist is empty — no candidates to enrich.")
    return candidates


# ── HARDBLOCK-4: Identity Verification ─────────────────────────────────────────


def verify_identity(input_email: str, enriched_email: str | None) -> bool:
    """Check that Apollo-returned email shares the same domain as the input.

    Returns True if identity is verified (safe to use enrichment data).
    Returns True if Apollo didn't return an email (we keep other fields).
    Returns False only if Apollo returned a *different* domain.
    """
    if not enriched_email or not input_email:
        return True
    input_domain = input_email.split("@")[-1].lower()
    enriched_domain = enriched_email.split("@")[-1].lower()
    return input_domain == enriched_domain


# ── Core Enrichment ────────────────────────────────────────────────────────────


async def enrich_candidates(
    candidates: list[dict],
    commit: bool = False,
    enricher: WaterfallEnricher | None = None,
    ghl: GHLClient | None = None,
) -> list[dict[str, Any]]:
    """Enrich a list of whitelist candidates via Apollo.

    HARDBLOCK-2: Only uses WaterfallEnricher.enrich() which calls
    apollo_client.get_person_detail() — never search_people().

    HARDBLOCK-3: Returns enrichment records only — no drafts, no campaigns.

    HARDBLOCK-5: Only writes to GHL if commit=True.
    """
    own_enricher = enricher is None
    own_ghl = ghl is None and commit
    if own_enricher:
        enricher = WaterfallEnricher()
    if own_ghl:
        ghl = GHLClient()

    results: list[dict[str, Any]] = []

    for i, candidate in enumerate(candidates):
        ghl_id = candidate["ghl_contact_id"]
        email = candidate.get("email", "")
        first_name = candidate.get("first_name", "")
        last_name = candidate.get("last_name", "")
        company_name = candidate.get("company_name", "")

        print(f"  [{i+1}/{len(candidates)}] Enriching {email}...", end=" ")

        try:
            record: EnrichmentRecord = await enricher.enrich(
                contact_id=ghl_id,
                email=email,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None,
                company_name=company_name if company_name else None,
            )
        except Exception as e:
            print(f"FAILED: {e}")
            results.append({
                "ghl_contact_id": ghl_id,
                "email": email,
                "status": "ENRICHMENT_FAILED",
                "error": str(e),
            })
            continue

        # HARDBLOCK-4: Identity verification
        identity_ok = verify_identity(email, record.email)
        identity_status = "VERIFIED" if identity_ok else "IDENTITY_MISMATCH"

        result_entry: dict[str, Any] = {
            "ghl_contact_id": ghl_id,
            "email": email,
            "enrichment_score": record.enrichment_score,
            "enrichment_grade": record.enrichment_grade.value,
            "fields_filled": record.fields_filled,
            "fields_total": record.fields_total,
            "apollo_status": record.waterfall_trace.apollo.value,
            "identity_check": identity_status,
            "enriched_data": {
                "company_name": record.company_name,
                "title": record.title,
                "industry": record.industry,
                "company_size": record.company_size,
                "revenue": record.revenue,
                "linkedin_url": record.linkedin_url,
            },
            "ghl_writeback": "SKIPPED",
        }

        grade_label = record.enrichment_grade.value
        print(f"{grade_label} (score={record.enrichment_score}, fields={record.fields_filled}/{record.fields_total}) [{identity_status}]")

        # GHL writeback — HARDBLOCK-5: only if --commit and identity OK
        if commit and identity_ok and ghl:
            try:
                tags = ["revtry-enriched"]
                await ghl.upsert_contact(
                    email=email,
                    first_name=first_name or "",
                    last_name=last_name or "",
                    company_name=record.company_name or company_name or "",
                    tags=tags,
                )
                result_entry["ghl_writeback"] = "WRITTEN"
                print(f"    → GHL upsert OK")
            except Exception as e:
                result_entry["ghl_writeback"] = f"FAILED: {e}"
                print(f"    → GHL upsert FAILED: {e}")
        elif commit and not identity_ok:
            result_entry["ghl_writeback"] = "BLOCKED_IDENTITY_MISMATCH"
            print(f"    → GHL writeback BLOCKED (identity mismatch)")

        results.append(result_entry)

    if own_enricher:
        await enricher.close()
    if own_ghl and ghl:
        await ghl.close()

    return results


# ── Report Generation ──────────────────────────────────────────────────────────


def write_enrichment_report(
    results: list[dict[str, Any]],
    commit: bool,
    outputs_dir: str | None = None,
) -> str:
    """Write enrichment report to outputs/ghl_enrichment_report.md."""
    base = Path(outputs_dir) if outputs_dir else Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    path = base / "ghl_enrichment_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Grade breakdown
    grades = {"READY": 0, "PARTIAL": 0, "MINIMAL": 0, "REJECT": 0, "ENRICHMENT_FAILED": 0}
    for r in results:
        grade = r.get("enrichment_grade", r.get("status", "ENRICHMENT_FAILED"))
        grades[grade] = grades.get(grade, 0) + 1

    writeback_count = sum(1 for r in results if r.get("ghl_writeback") == "WRITTEN")
    identity_mismatches = sum(1 for r in results if r.get("identity_check") == "IDENTITY_MISMATCH")

    lines = [
        "# GHL Follow-Up Enrichment Report",
        "",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Mode**: {'COMMIT (writes to GHL)' if commit else 'DRY RUN (no GHL writes)'}",
        f"**Candidates processed**: {len(results)}",
        "",
        "---",
        "",
        "## Enrichment Grade Breakdown",
        "",
        "| Grade | Count | Description |",
        "|-------|-------|-------------|",
        f"| READY | {grades['READY']} | 90-100% fields filled |",
        f"| PARTIAL | {grades['PARTIAL']} | 70-89% fields filled |",
        f"| MINIMAL | {grades['MINIMAL']} | 50-69% fields filled |",
        f"| REJECT | {grades['REJECT']} | <50% fields filled |",
        f"| FAILED | {grades['ENRICHMENT_FAILED']} | Apollo call failed |",
        "",
        "## Identity & Writeback",
        "",
        f"- Identity mismatches: **{identity_mismatches}**",
        f"- GHL writebacks: **{writeback_count}** / {len(results)}",
        "",
        "---",
        "",
        "## Per-Contact Results",
        "",
        "| # | Email | Score | Grade | Fields | Apollo | Identity | GHL |",
        "|---|-------|-------|-------|--------|--------|----------|-----|",
    ]

    for i, r in enumerate(results, 1):
        email = r.get("email", "N/A")
        score = r.get("enrichment_score", "N/A")
        grade = r.get("enrichment_grade", r.get("status", "N/A"))
        fields = f"{r.get('fields_filled', '?')}/{r.get('fields_total', '?')}"
        apollo = r.get("apollo_status", "N/A")
        identity = r.get("identity_check", "N/A")
        ghl_wb = r.get("ghl_writeback", "N/A")
        lines.append(f"| {i} | {email} | {score} | {grade} | {fields} | {apollo} | {identity} | {ghl_wb} |")

    lines.extend(["", "---", ""])

    # Enriched data details for contacts with data
    lines.append("## Enriched Data Details")
    lines.append("")
    for r in results:
        data = r.get("enriched_data")
        if not data:
            continue
        filled_fields = {k: v for k, v in data.items() if v}
        if filled_fields:
            lines.append(f"### {r['email']}")
            for k, v in filled_fields.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")
    print(f"\nReport written: {path}")
    return str(path)


# ── Main ───────────────────────────────────────────────────────────────────────


async def run(commit: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    """Main entry point for enrichment."""
    print("=" * 60)
    print("GHL FOLLOW-UP ENRICHMENT")
    print(f"Mode: {'COMMIT' if commit else 'DRY RUN'}")
    print("=" * 60)

    # HARDBLOCK-1: Load whitelist
    candidates = load_whitelist()
    print(f"Whitelist loaded: {len(candidates)} candidates")

    if limit:
        candidates = candidates[:limit]
        print(f"Limiting to first {limit} candidates")

    print()

    # HARDBLOCK-2 + 3 + 4: Enrich (no recon, no campaigns, identity check)
    results = await enrich_candidates(candidates, commit=commit)

    # Write report
    write_enrichment_report(results, commit=commit)

    # Summary
    print(f"\n{'=' * 60}")
    print("ENRICHMENT SUMMARY")
    print(f"{'=' * 60}")
    grades = {}
    for r in results:
        g = r.get("enrichment_grade", r.get("status", "FAILED"))
        grades[g] = grades.get(g, 0) + 1
    for g, count in sorted(grades.items()):
        print(f"  {g}: {count}")
    writeback_count = sum(1 for r in results if r.get("ghl_writeback") == "WRITTEN")
    if commit:
        print(f"  GHL writebacks: {writeback_count}/{len(results)}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Enrich GHL follow-up candidates via Apollo")
    parser.add_argument("--commit", action="store_true", help="Write enrichment data back to GHL")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N candidates")
    args = parser.parse_args()

    asyncio.run(run(commit=args.commit, limit=args.limit))


if __name__ == "__main__":
    main()
