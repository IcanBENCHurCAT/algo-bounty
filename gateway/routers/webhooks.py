import os
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..github import handle_issue_event, handle_pr_event, validate_webhook
from ..dependencies import get_db

router = APIRouter(prefix="/webhooks/github", tags=["webhooks"])

@router.post("", summary="GitHub webhook handler", description="Endpoint for receiving GitHub webhooks (issues, pull_request). Processes bounty creation from issues and claiming/submission from PRs.")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    GitHub Webhook receiver.
    Uses pre-verified payload from GitHubWebhookSignatureMiddleware.
    """
    event_type = request.headers.get("X-GitHub-Event", "")

    # Retrieve payload from middleware
    payload = getattr(request.state, "github_payload", None)

    if payload is None:
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "Missing or invalid payload"}
        )

    # --- Dispatch ---
    if event_type == "issues":
        await handle_issue_event(db, payload)
    elif event_type == "pull_request":
        await handle_pr_event(db, payload)
    elif event_type == "issue_comment":
        await handle_issue_event(db, payload)
    elif event_type == "pull_request_review":
        await handle_pr_event(db, payload)

    return {"status": "event_processed"}
