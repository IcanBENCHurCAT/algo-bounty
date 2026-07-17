import os
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..github import handle_issue_event, handle_pr_event, validate_webhook
from ..dependencies import get_db
from ..database import WebhookDeliveryRecord

router = APIRouter(prefix="/webhooks/github", tags=["webhooks"])

@router.post("", summary="GitHub webhook handler", description="Endpoint for receiving GitHub webhooks (issues, pull_request). Processes bounty creation from issues and claiming/submission from PRs.")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    GitHub Webhook receiver.
    Uses pre-verified payload from GitHubWebhookSignatureMiddleware.

    Idempotency: The X-GitHub-Delivery header uniquely identifies each webhook
    delivery. We persist it to webhook_delivery_records on first receipt and
    return 200 immediately for replays (FR-004 / T020).
    """
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    # --- Idempotency guard (FR-004) ---
    if delivery_id:
        existing = db.query(WebhookDeliveryRecord).filter(
            WebhookDeliveryRecord.delivery_id == delivery_id
        ).first()
        if existing:
            # Already processed — return 200 immediately, do nothing
            return {"status": "already_processed", "delivery_id": delivery_id}

        # Record this delivery before processing so concurrent replays are blocked
        record = WebhookDeliveryRecord(delivery_id=delivery_id, status="processing")
        db.add(record)
        try:
            db.commit()
        except Exception:
            # Unique constraint violation: another request beat us to it
            db.rollback()
            return {"status": "already_processed", "delivery_id": delivery_id}

    # Retrieve payload from middleware
    payload = getattr(request.state, "github_payload", None)

    if payload is None:
        # Mark delivery as failed if we recorded it
        if delivery_id:
            _update_delivery_status(db, delivery_id, "failed")
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "Missing or invalid payload"}
        )

    # --- Dispatch ---
    try:
        if event_type == "issues":
            await handle_issue_event(db, payload)
        elif event_type == "pull_request":
            await handle_pr_event(db, payload)
        elif event_type == "issue_comment":
            await handle_issue_event(db, payload)
        elif event_type == "pull_request_review":
            await handle_pr_event(db, payload)

        # Mark delivery as successfully processed
        if delivery_id:
            _update_delivery_status(db, delivery_id, "success")

    except Exception as exc:
        if delivery_id:
            _update_delivery_status(db, delivery_id, "failed")
        raise exc

    return {"status": "event_processed"}


def _update_delivery_status(db: Session, delivery_id: str, status: str) -> None:
    """Update the delivery record status after processing."""
    try:
        record = db.query(WebhookDeliveryRecord).filter(
            WebhookDeliveryRecord.delivery_id == delivery_id
        ).first()
        if record:
            record.status = status
            db.commit()
    except Exception:
        db.rollback()
