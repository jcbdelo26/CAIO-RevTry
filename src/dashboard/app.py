"""FastAPI approval dashboard for campaign drafts.

Endpoints:
- GET /        — HTML dashboard with draft list, filters, summary counts
- GET /drafts  — JSON array of all drafts
- GET /drafts/{id} — HTML detail with email preview + approve/reject buttons
- POST /drafts/{id}/approve — Mark APPROVED, push to GHL, record timestamp
- POST /drafts/{id}/reject  — Mark REJECTED, write feedback file
- POST /drafts/batch/approve — Batch approve selected drafts
- POST /drafts/batch/reject  — Batch reject selected drafts
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

app = FastAPI(title="RevTry Dashboard", version="0.2.0")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
