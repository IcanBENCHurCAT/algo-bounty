import hmac
import hashlib
import logging
import re
import json
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from .database import Bounty, GitHubPR, Notification, Agent
from .algod_client import NODE_ENV

logger = logging.getLogger(__name__)

# Known GitHub webhook event types (non-exhaustive)
KNOWN_EVENT_TYPES = {
    "check_run", "check_suite", "commit_comment", "create", "delete",
    "deployment", "deployment_status", "fork", "gollum",
    "installation", "installation_repositories", "issue_comment",
    "issues", "member", "membership", "milestone", "organization",
    "org_block", "page_build", "ping", "project", "project_card",
    "project_column", "public", "pull_request", "pull_request_review",
    "pull_request_review_comment", "pull_request_review_thread",
    "push", "release", "repository", "secret_scanning_alert",
    "status", "team", "team_add", "watch", "workflow_dispatch",
    "workflow_run",
}

# Regex pattern to match #ALGO-XXXX or ALGO-XXXX
BOUNTY_RE = re.compile(r'#?ALGO-(\d+)')

def verify_webhook_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """
    Verify that a GitHub webhook request includes a valid HMAC-SHA256 signature.

    GitHub sends the signature in the X-Hub-Signature-256 header:
        X-Hub-Signature-256: sha256=<hex_digest>

    Args:
        payload_bytes: Raw request body bytes
        signature: The X-Hub-Signature-256 header value (e.g. "sha256=abcd...")
        secret: The webhook secret string

    Returns:
        True if the signature is valid, False otherwise
    """
    if not secret or not signature:
        return False

    # Extract hex digest after "sha256="
    expected = "sha256="
    if not signature.startswith(expected):
        return False
    expected_hex = signature[len(expected):]

    # Compute HMAC-SHA256
    computed = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, expected_hex)


def validate_webhook(event_type: str, secret: str, signature: str,
                     delivery_id: str, raw_body: bytes,
                     client_ip: str) -> tuple:
    """
    Full webhook validation pipeline.

    Returns:
        (ok: bool, reason: str)
        - ok=True  → signature valid and event type known; reason contains delivery_id
        - ok=False → validation failed; reason contains the failure reason
    """
    # 1. Check if secret is configured
    secret_configured = bool(secret)
    if not secret_configured:
        if NODE_ENV == "sandbox":
            logger.warning(
                "GitHub webhook signature verification SKIPPED: "
                "GITHUB_WEBHOOK_SECRET is not set (dev mode)."
            )
            return True, delivery_id
        else:
            logger.error(
                f"GitHub webhook REJECTED: GITHUB_WEBHOOK_SECRET is not set in {NODE_ENV} mode "
                f"(delivery={delivery_id}, ip={client_ip})"
            )
            return False, "GITHUB_WEBHOOK_SECRET not configured"

    # 2. Validate event type
    if not event_type:
        logger.warning(
            f"GitHub webhook REJECTED: missing X-GitHub-Event header "
            f"(delivery={delivery_id}, ip={client_ip})"
        )
        return False, "Missing X-GitHub-Event header"

    if event_type not in KNOWN_EVENT_TYPES:
        logger.warning(
            f"GitHub webhook REJECTED: unknown event type '{event_type}' "
            f"(delivery={delivery_id}, ip={client_ip})"
        )
        return False, f"Unknown event type: {event_type}"

    # 3. Validate HMAC signature (constant-time comparison)
    if not verify_webhook_signature(raw_body, signature, secret):
        logger.warning(
            f"GitHub webhook REJECTED: invalid signature "
            f"(delivery={delivery_id}, ip={client_ip}, event={event_type})"
        )
        return False, "Invalid webhook signature"

    logger.info(
        f"GitHub webhook OK: event={event_type} delivery={delivery_id}"
    )
    return True, delivery_id


def log_bot_comment(repo_url: str, issue_or_pr_number: int, comment_text: str):
    """
    Mock GitHub app comment.
    Writes bot comments to a log file and prints to stdout for local inspection.
    """
    log_file = "github_bot_comments.log"
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "repo_url": repo_url,
        "number": issue_or_pr_number,
        "comment": comment_text
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
    print(f"\n[MOCK GITHUB BOT] Commented on {repo_url}#{issue_or_pr_number}:\n{comment_text}\n")

def handle_issue_event(db: Session, payload: dict):
    """
    Handle GitHub issue webhook events.
    Convert issue to pending bounty if it has a 'bounty' label or title tag.
    """
    action = payload.get("action")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    
    if action not in ["opened", "labeled"]:
        return

    labels = [label.get("name") for label in issue.get("labels", [])]
    title = issue.get("title", "")
    
    # Check if this issue is meant to be a bounty
    is_bounty = "bounty" in labels or "algo-bounty" in labels or title.startswith("[ALGO-BOUNTY]")
    if not is_bounty:
        return
        
    # Generate bounty_id from issue ID or node_id
    issue_number = issue.get("number")
    bounty_id = f"b_{issue_number}"
    
    # Check if bounty already exists
    existing = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if existing:
        return
        
    # Extract amount from body (fallback to 10 ALGO = 10,000,000 microALGO)
    body = issue.get("body", "") or ""
    amount = 10000000  # Default 10 ALGO
    match = re.search(r'(?:amount|price|bounty):\s*(\d+)', body, re.IGNORECASE)
    if match:
        amount = int(match.group(1))
        
    is_hitm = "hitm" in body.lower()
    
    # Create bounty in pending_payment state
    bounty = Bounty(
        bounty_id=bounty_id,
        app_id=None,  # Not deployed yet
        status="pending_payment",
        creator=issue.get("user", {}).get("login", "unknown_creator"),
        amount=amount,
        asset_id=0,
        is_hitm=is_hitm,
        description=issue.get("title", "") + "\n\n" + body[:200],
        repo_url=repo.get("html_url", ""),
        karma_requirement=0
    )
    db.add(bounty)
    db.commit()
    
    # Post Bot comment on GitHub issue
    comment_text = (
        f"🎯 **AlgoBounty Detected**\n\n"
        f"An issue has been flagged as a bounty!\n"
        f"- **Proposed Amount**: {amount / 1_000_000} ALGO\n"
        f"- **Status**: Pending Payment (Deploy escrow to activate)\n"
        f"- **Bounty ID**: `ALGO-{issue_number}`\n\n"
        f"[📋 Deploy Escrow & Activate on Dashboard](http://localhost:8000/dashboard?bounty_id={bounty_id})"
    )
    log_bot_comment(bounty.repo_url, issue_number, comment_text)

def handle_pr_event(db: Session, payload: dict):
    """
    Handle GitHub pull request webhook events.
    Auto-claims or links bounty based on PR references.
    """
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    
    if action not in ["opened", "synchronize", "closed"]:
        return
        
    title = pr.get("title", "")
    body = pr.get("body", "") or ""
    pr_number = pr.get("number")
    author = pr.get("user", {}).get("login")
    
    # Scan for #ALGO-XXXX or ALGO-XXXX
    text_to_scan = f"{title} {body}"
    match = BOUNTY_RE.search(text_to_scan)
    if not match:
        return
        
    issue_number = match.group(1)
    bounty_id = f"b_{issue_number}"
    
    # Find the corresponding bounty
    bounty = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    if not bounty:
        return
        
    # Link PR to bounty
    existing_pr = db.query(GitHubPR).filter(
        GitHubPR.pr_number == pr_number, 
        GitHubPR.repo_url == repo.get("html_url", "")
    ).first()
    
    if not existing_pr:
        new_pr = GitHubPR(
            pr_number=pr_number,
            repo_url=repo.get("html_url", ""),
            bounty_id=bounty_id,
            state=pr.get("state", "open"),
            author=author
        )
        db.add(new_pr)
        
    # Handle PR lifecycle actions
    if action in ["opened", "synchronize"]:
        # If bounty is open, auto-claim it for this worker if not already claimed
        if bounty.status == "open":
            bounty.status = "claimed"
            bounty.worker = author  # Map github username as mock worker address (or link via DB)
            db.commit()
            
            comment_text = (
                f"🤝 **Bounty Claimed!**\n\n"
                f"GitHub user @{author} has claimed this bounty by opening PR #{pr_number}.\n"
                f"The bounty status has transitioned to **CLAIMED**.\n"
                f"Submit your work on the dashboard to trigger review."
            )
            log_bot_comment(bounty.repo_url, int(issue_number), comment_text)
            
        # If bounty is claimed, transition to submitted
        elif bounty.status == "claimed" and bounty.worker == author:
            bounty.status = "submitted"
            db.commit()
            
            comment_text = (
                f"🚀 **Solution Submitted!**\n\n"
                f"Worker @{author} has submitted their PR #{pr_number} for review.\n"
                f"The bounty status is now **SUBMITTED**.\n"
                f"- **HITM Review**: {'Enabled (7-day window)' if bounty.is_hitm else 'Disabled (Trustless auto-release)'}"
            )
            log_bot_comment(bounty.repo_url, int(issue_number), comment_text)
            
            # Notify creator
            creator_notif = Notification(
                recipient=bounty.creator,
                message=f"Bounty ALGO-{issue_number} has a new solution submitted by GitHub user @{author}."
            )
            db.add(creator_notif)
            db.commit()
            
    elif action == "closed" and pr.get("merged") is True:
        # PR Merged! If trustless mode is on, auto-approve the payout!
        if bounty.status in ["claimed", "submitted"]:
            if not bounty.is_hitm:
                # Trustless mode: auto payout!
                bounty.status = "closed"
                bounty.payout_type = "PAYOUT"
                db.commit()
                
                comment_text = (
                    f"🎉 **Bounty Completed & Funds Released!**\n\n"
                    f"PR #{pr_number} has been merged. Since this bounty was in **Trustless Mode**, "
                    f"the escrow has been closed, and funds have been automatically released to @{author}!"
                )
                log_bot_comment(bounty.repo_url, int(issue_number), comment_text)
                
                # Reward karma
                worker_agent = db.query(Agent).filter(Agent.address == author).first()
                if worker_agent:
                    worker_agent.karma += 5
                    worker_agent.completed_bounties += 1
                    db.commit()
            else:
                # HITM mode: require human approval, remind creator
                comment_text = (
                    f"⚠️ **PR Merged - Awaiting Escrow Release**\n\n"
                    f"PR #{pr_number} has been merged, but this bounty is in **HITM Mode** (Human-in-the-Middle).\n"
                    f"Creator @{bounty.creator} must sign the release transaction on the dashboard to pay the worker."
                )
                log_bot_comment(bounty.repo_url, int(issue_number), comment_text)
