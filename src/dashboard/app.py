"""FastAPI approval dashboard for campaign drafts.

Endpoints:
- GET /        — HTML dashboard with draft list (PENDING first)
- GET /drafts  — JSON array of all drafts
- GET /drafts/{id} — HTML detail with email preview + approve/reject buttons
- POST /drafts/{id}/approve — Mark APPROVED, record timestamp
- POST /drafts/{id}/reject  — Mark REJECTED, write feedback file
"""

from __future__ import annotations

from pathlib import Path

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

app = FastAPI(title="RevTry Dashboard", version="0.1.0")

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    drafts = list_drafts()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "drafts": drafts},
    )


@app.get("/drafts")
async def list_drafts_api():
    drafts = list_drafts()
    return [d.model_dump(by_alias=True) for d in drafts]


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
