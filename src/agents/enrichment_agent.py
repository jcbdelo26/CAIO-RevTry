"""Enrichment Agent — Apollo enrichment per contact.

Takes recon records and enriches via Apollo (primary).
BetterContact and Clay fallbacks are deferred. Produces EnrichmentOutput.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from models.schemas import (
    EnrichmentGrade,
    EnrichmentOutput,
    EnrichmentRecord,
    EnrichmentTrace,
    ReconRecord,
)
from integrations.waterfall import WaterfallEnricher


async def run_enrichment(
    task_id: str,
    records: list[ReconRecord],
    enricher: Optional[WaterfallEnricher] = None,
) -> EnrichmentOutput:
    """Enrich a batch of recon records via the waterfall."""
    if enricher is None:
        enricher = WaterfallEnricher()

    enriched: list[EnrichmentRecord] = []

    for record in records:
        # Use email as contact_id if available, otherwise apollo_id or name
        contact_id = (
            record.email
            or record.apollo_id
            or f"{record.first_name}_{record.last_name}@{record.company_name}"
        )

        result = await enricher.enrich(
            contact_id=contact_id,
            apollo_id=record.apollo_id,
            email=record.email,
            first_name=record.first_name,
            last_name=record.last_name if record.last_name and "*" not in record.last_name else None,
            company_name=record.company_name,
            linkedin_url=record.linkedin_url,
        )
        enriched.append(result)

    # Compute trace counts
    ready = sum(1 for r in enriched if r.enrichment_grade == EnrichmentGrade.READY)
    partial = sum(1 for r in enriched if r.enrichment_grade == EnrichmentGrade.PARTIAL)
    minimal = sum(1 for r in enriched if r.enrichment_grade == EnrichmentGrade.MINIMAL)
    rejected = sum(1 for r in enriched if r.enrichment_grade == EnrichmentGrade.REJECT)

    return EnrichmentOutput(
        taskId=task_id,
        agent="enrichment",
        timestamp=datetime.now(timezone.utc).isoformat(),
        records=enriched,
        count=len(enriched),
        trace=EnrichmentTrace(
            vaultFilesUsed=[
                "vault/integrations/apollo.md",
            ],
            recordsReceived=len(records),
            recordsReady=ready,
            recordsPartial=partial,
            recordsMinimal=minimal,
            recordsRejected=rejected,
        ),
    )
