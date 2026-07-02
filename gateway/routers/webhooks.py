import os
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..github import handle_issue_event, handle_pr_event, validate_webhook
from ..dependencies import get_db

router = APIRouter(prefix="/webhooks/github", tags=["webhooks"])

@router.post("")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    GitHub Webhook receiver.
    Verifies HMAC-SHA256 signature via X-Hub-Signature-256 header,
    validates event type, then dispatches.
    """
    # --- Signature verification (MUST be first) ---
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    client_ip = request.client.host if request.client else "unknown"

    # Read raw body BEFORE calling .json()
    raw_body = await request.body()

    ok, reason = validate_webhook(
        event_type=event_type,
        secret=secret,
        signature=signature,
        delivery_id=delivery_id,
        raw_body=raw_body,
        client_ip=client_ip,
    )
    if not ok:
        return JSONResponse(
            status_code=403,
            content={"status": "rejected", "reason": reason}
        )

    # --- Parse payload ---
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "Invalid JSON payload"}
        )

    # --- Dispatch ---
    if event_type == "issues":
        handle_issue_event(db, payload)
    elif event_type == "pull_request":
        handle_pr_event(db, payload)
    elif event_type == "issue_comment":
        handle_issue_event(db, payload)
    elif event_type == "pull_request_review":
        handle_pr_event(db, payload)

    return {"status": "event_processed"}
