"""GHL service layer — encapsulates the 'on approval' workflow.

When a draft is approved, upsert the contact in GHL and create a follow-up task.
Best-effort: if GHL push fails, return an error dict instead of raising.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from integrations.ghl_client import GHLClient
from models.schemas import StoredDraft

logger = logging.getLogger(__name__)


async def push_approved_draft_to_ghl(
    draft: StoredDraft,
    ghl: Optional[GHLClient] = None,
) -> dict[str, Any]:
    """Upsert contact in GHL and create a follow-up task.

    Returns:
        {"status": "pushed", "ghl_contact_id": ..., "ghl_task_id": ...}
        or {"status": "ghl_push_failed", "error": ...}
    """
    owns_client = ghl is None
    if ghl is None:
        ghl = GHLClient()

    try:
        # Determine if contact_id is a GHL ID or an email
        is_email = "@" in draft.contact_id

        if is_email:
            # Cold pipeline: contact_id is email — upsert to get GHL contact ID
            upsert_result = await ghl.upsert_contact(
                email=draft.contact_id,
            )
            contact = upsert_result.get("contact", {})
            ghl_contact_id = contact.get("id", "")
        else:
            # GHL pipeline: contact_id IS the GHL contact ID — skip upsert
            ghl_contact_id = draft.contact_id

        if not ghl_contact_id:
            raise RuntimeError("GHL contact ID missing after approval write path.")

        await ghl.add_contact_tag(ghl_contact_id, "revtry-approved")

        # Best-effort: create follow-up task (failure must not block dispatch)
        task_id = ""
        task_error = ""
        try:
            task_result = await ghl.create_task(
                contact_id=ghl_contact_id,
                title=f"Follow up: {draft.subject}",
                description=(
                    f"Approved draft for {draft.contact_id}\n"
                    f"Tier: {draft.icp_tier} | Channel: {draft.channel.value}\n"
                    f"Angle: {draft.angle_id}"
                ),
            )
            task_id = task_result.get("task", {}).get("id", "")
        except Exception as task_exc:
            logger.warning("GHL task creation failed for draft %s: %s", draft.draft_id, task_exc)
            task_error = str(task_exc)

        return {
            "status": "pushed",
            "ghl_contact_id": ghl_contact_id,
            "ghl_task_id": task_id,
            **({"task_error": task_error} if task_error else {}),
        }

    except Exception as exc:
        logger.warning("GHL push failed for draft %s: %s", draft.draft_id, exc)
        return {
            "status": "ghl_push_failed",
            "error": str(exc),
        }
    finally:
        if owns_client:
            await ghl.close()
