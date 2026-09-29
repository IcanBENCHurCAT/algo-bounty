"""
Terms of Service endpoints (Legal #171).

Provides:
  - GET /api/v1/terms/current — current active ToS version + text
  - GET /api/v1/terms/{version} — historical ToS lookup
  - POST /api/v1/terms/accept — record user acceptance
  - GET /api/v1/terms/accepted/{address} — check if user has accepted
  - POST /api/v1/blacklist — admin-only: add to blacklist
  - POST /api/v1/blacklist/{address}/resolve — resolve/unblacklist
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import Agent
from ..auth import get_current_user, is_admin
from ..config import settings
from ..dependencies import get_db
from ..supabase_migration import (
    CURRENT_TOS_VERSION,
    CURRENT_TOS_HASH,
    _TOS_TEXT_1_1_0,
    PLATFORM_GOVERNING_LAW,
    PLATFORM_ARBITRATION_PROC,
)

router = APIRouter(prefix="/api/v1/terms", tags=["terms"])

# ─── Current ToS content ──────────────────────────────────────────

TOS_CONTENT_1_1_0 = _TOS_TEXT_1_1_0


@router.get("/current", summary="Get current ToS", description="Returns the currently active Terms of Service version and full text.")
def get_current_terms(db: Session = Depends(get_db)):
    """Return the current active ToS."""
    return {
        "version": CURRENT_TOS_VERSION,
        "text": TOS_CONTENT_1_1_0,
        "sha256_hash": CURRENT_TOS_HASH,
        "effective_date": datetime.now(timezone.utc).isoformat(),
        "governing_law": PLATFORM_GOVERNING_LAW,
        "arbitration_procedure": PLATFORM_ARBITRATION_PROC,
    }


@router.get("/{version}", summary="Get historical ToS", description="Returns a specific version of the Terms of Service.")
def get_terms_version(version: str, db: Session = Depends(get_db)):
    """Return a historical ToS version."""
    if version == "1.1.0":
        return {
            "version": "1.1.0",
            "text": TOS_CONTENT_1_1_0,
            "sha256_hash": CURRENT_TOS_HASH,
        }
    raise HTTPException(status_code=404, detail=f"Terms version {version} not found")


@router.post("/accept", summary="Accept current ToS", description="Records a user's acceptance of the current Terms of Service.")
def accept_terms(
    address: str,
    db: Session = Depends(get_db),
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """
    Record that an address has accepted the current ToS.
    Idempotent: calling again is safe (no error, just confirms acceptance).
    """
    # Check if already accepted current version
    from ..supabase_migration import Base
    # We use raw SQL to avoid ORM model mismatch
    from sqlalchemy import text
    result = db.execute(
        text("SELECT id FROM user_terms_acceptance WHERE address = :addr AND terms_version = :ver LIMIT 1"),
        {"addr": address, "ver": CURRENT_TOS_VERSION}
    ).first()

    if result:
        # Already accepted — idempotent return
        return {
            "accepted": True,
            "version": CURRENT_TOS_VERSION,
            "accepted_at": result[0] if isinstance(result[0], str) else None,
        }

    # Record acceptance
    ip_hash = sha256((ip_address or "unknown").encode()).hexdigest()[:16] if ip_address else None
    ua_hash = sha256((user_agent or "unknown").encode()).hexdigest()[:16] if user_agent else None

    db.execute(
        text("""
            INSERT INTO user_terms_acceptance (address, terms_version, accepted_ip_hash, user_agent_hash)
            VALUES (:addr, :ver, :iph, :uah)
        """),
        {"addr": address, "ver": CURRENT_TOS_VERSION, "iph": ip_hash, "uah": ua_hash}
    )
    db.commit()

    return {
        "accepted": True,
        "version": CURRENT_TOS_VERSION,
        "message": "Terms accepted successfully",
    }


@router.get("/accepted/{address}", summary="Check acceptance status", description="Checks whether a wallet address has accepted the current ToS.")
def check_acceptance(address: str, db: Session = Depends(get_db)):
    """Check if an address has accepted current ToS."""
    from sqlalchemy import text
    result = db.execute(
        text("SELECT accepted_at FROM user_terms_acceptance WHERE address = :addr AND terms_version = :ver LIMIT 1"),
        {"addr": address, "ver": CURRENT_TOS_VERSION}
    ).first()

    if result:
        return {"accepted": True, "accepted_at": result[0].isoformat() if hasattr(result[0], 'isoformat') else str(result[0])}

    return {
        "accepted": False,
        "current_version": CURRENT_TOS_VERSION,
        "requires_action": True,
    }


@router.post("/enforce", summary="Check enforcement for user", description="Checks if a user has accepted ToS. Returns 451 if not.")
def enforce_terms_check(
    address: str,
    db: Session = Depends(get_db),
):
    """
    Pre-flight check for bounty creation endpoints.
    Call this before any write operation. Returns 451 if user hasn't accepted.
    """
    from sqlalchemy import text
    result = db.execute(
        text("SELECT accepted_at FROM user_terms_acceptance WHERE address = :addr AND terms_version = :ver LIMIT 1"),
        {"addr": address, "ver": CURRENT_TOS_VERSION}
    ).first()

    if not result:
        raise HTTPException(
            status_code=451,
            detail={
                "reason": "Terms Not Accepted",
                "current_version": CURRENT_TOS_VERSION,
                "terms_text": TOS_CONTENT_1_1_0,
                "accept_url": f"/api/v1/terms/accept?address={address}",
                "message": "You must accept the Terms of Service before creating bounties.",
            }
        )

    return {"accepted": True, "version": CURRENT_TOS_VERSION}


@router.get("/blacklist", summary="List blacklist", description="Admin-only: list all blacklisted addresses.")
def list_blacklist(
    db: Session = Depends(get_db),
    current_user: str = Depends(is_admin),
):
    """List all blacklisted addresses."""
    from sqlalchemy import text
    results = db.execute(
        text("SELECT address, reason, blacklisted_at, status FROM user_blacklist WHERE status = 'active' ORDER BY blacklisted_at DESC")
    ).all()

    return {
        "blacklisted_addresses": [
            {
                "address": r[0],
                "reason": r[1],
                "blacklisted_at": r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2]),
                "status": r[3],
            }
            for r in results
        ]
    }


@router.post("/blacklist", summary="Add to blacklist", description="Admin-only: blacklist an address.")
def add_to_blacklist(
    address: str,
    reason: str = ...,
    details: Optional[str] = None,
    expires_at: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(is_admin),
):
    """Blacklist an address (blocks from new bounties)."""
    from sqlalchemy import text

    db.execute(
        text("""
            INSERT INTO user_blacklist (address, reason, details, blacklisted_by, expires_at, status)
            VALUES (:addr, :reason, :details, :by, :exp, 'active')
        """),
        {
            "addr": address,
            "reason": reason,
            "details": details,
            "by": current_user,
            "exp": expires_at,
        }
    )
    db.commit()

    return {
        "blacklisted": True,
        "address": address,
        "reason": reason,
        "blacklisted_by": current_user,
    }


@router.post("/blacklist/{address}/resolve", summary="Resolve blacklist", description="Admin-only: remove address from blacklist.")
def resolve_blacklist(
    address: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(is_admin),
):
    """Remove an address from the blacklist."""
    from sqlalchemy import text

    db.execute(
        text("""
            UPDATE user_blacklist SET
                status = 'resolved',
                resolved_by = :by,
                resolved_at = NOW(),
                resolution_note = :note
            WHERE address = :addr AND status = 'active'
        """),
        {"addr": address, "by": current_user, "note": reason}
    )
    db.commit()

    return {
        "blacklist_removed": True,
        "address": address,
        "resolved_by": current_user,
    }
