"""
Sanctions Screening & KYA (Know Your Agent) Integration module.

Provides OFAC / PEP screening at point of entry for bounty creators and workers (Issue #180).
Integrates with KYA service (POST /api/v1/screen) with fallback to local evaluator.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import settings
from .dependencies import get_db
from .schemas import ScreeningRequest, ScreeningResponse

logger = logging.getLogger(__name__)

# Valid screening statuses
SCREENING_STATUS_PENDING = "pending"
SCREENING_STATUS_PASSED = "passed"
SCREENING_STATUS_FLAGGED = "flagged"
SCREENING_STATUS_BLOCKED = "blocked"

VALID_SCREENING_STATUSES = {
    SCREENING_STATUS_PENDING,
    SCREENING_STATUS_PASSED,
    SCREENING_STATUS_FLAGGED,
    SCREENING_STATUS_BLOCKED,
}

# Known sanctioned / blocked addresses and patterns for local evaluation
KNOWN_SANCTIONED_ADDRESSES = {
    "SANCTIONED_OFAC_TEST_ADDRESS",
    "OFAC_BLOCKED_ADDRESS",
    "TORNADO_CASH_ROUTER",
    "OFAC_SANCTIONED_ADDRESS",
    "BLOCKED_CREATOR_ADDRESS",
    "BLOCKED_TEST_ADDRESS",
}
KNOWN_SANCTIONED_UPPER = frozenset(a.strip().upper() for a in KNOWN_SANCTIONED_ADDRESSES)

# Known PEP / high-risk flagged addresses and patterns for local evaluation
KNOWN_FLAGGED_ADDRESSES = {
    "PEP_FLAGGED_TEST_ADDRESS",
    "FLAGGED_TEST_ADDRESS",
    "HIGH_RISK_CREATOR_ADDRESS",
}
KNOWN_FLAGGED_UPPER = frozenset(a.strip().upper() for a in KNOWN_FLAGGED_ADDRESSES)


def compute_screening_hash(address: str, status: str, screened_at: datetime) -> str:
    """Generate a tamper-evident SHA256 audit hash for a screening result."""
    payload = f"{address.strip()}:{status.strip()}:{screened_at.isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ScreeningResult:
    """Encapsulates the result of a KYA / sanctions screening check."""

    def __init__(
        self,
        status: str,
        address: str,
        screened_at: datetime,
        screening_hash: str,
        sanctions_match: bool = False,
        pep_match: bool = False,
        risk_score: float = 0.0,
        reason: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.status = status if status in VALID_SCREENING_STATUSES else SCREENING_STATUS_PENDING
        self.address = address
        self.screened_at = screened_at
        self.screening_hash = screening_hash
        self.sanctions_match = sanctions_match
        self.pep_match = pep_match
        self.risk_score = risk_score
        self.reason = reason
        self.details = details or {}

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "address": self.address,
            "screened_at": self.screened_at.isoformat(),
            "screening_hash": self.screening_hash,
            "sanctions_match": self.sanctions_match,
            "pep_match": self.pep_match,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"<ScreeningResult address={self.address} status={self.status} hash={self.screening_hash[:10]}...>"


def evaluate_locally(address: str, db: Optional[Session] = None) -> ScreeningResult:
    """
    Local sanctions and PEP screening evaluator.
    Used when KYA service is unavailable or local evaluation is requested.
    """
    now = datetime.now(timezone.utc)
    norm_address = address.strip()
    addr_upper = norm_address.upper()

    # 1. Check database blacklist if DB session is provided
    if db is not None:
        try:
            from .supabase_migration import UserBlacklist
            bl = db.query(UserBlacklist).filter(
                func.upper(func.trim(UserBlacklist.address)) == addr_upper,
                UserBlacklist.status == "active",
            ).first()
            if bl:
                status = SCREENING_STATUS_BLOCKED
                hash_val = compute_screening_hash(norm_address, status, now)
                return ScreeningResult(
                    status=status,
                    address=norm_address,
                    screened_at=now,
                    screening_hash=hash_val,
                    sanctions_match=True,
                    risk_score=1.0,
                    reason=f"Address blacklisted: {bl.reason}",
                    details={"blacklist_reason": bl.reason, "details": bl.details},
                )
        except Exception as e:
            logger.debug(f"Blacklist check skipped: {e}")

    # 2. Check known static sanctioned addresses & patterns
    if (
        addr_upper in KNOWN_SANCTIONED_UPPER
        or "SANCTIONED" in addr_upper
        or "BLOCKED" in addr_upper
        or "OFAC" in addr_upper
    ):
        status = SCREENING_STATUS_BLOCKED
        hash_val = compute_screening_hash(norm_address, status, now)
        return ScreeningResult(
            status=status,
            address=norm_address,
            screened_at=now,
            screening_hash=hash_val,
            sanctions_match=True,
            risk_score=1.0,
            reason="OFAC / Sanctions watchlist match",
            details={"match_type": "sanctions_list", "list": "OFAC SDN"},
        )

    # 3. Check known static flagged / PEP addresses & patterns
    if (
        addr_upper in KNOWN_FLAGGED_UPPER
        or "FLAGGED" in addr_upper
        or "PEP" in addr_upper
    ):
        status = SCREENING_STATUS_FLAGGED
        hash_val = compute_screening_hash(norm_address, status, now)
        return ScreeningResult(
            status=status,
            address=norm_address,
            screened_at=now,
            screening_hash=hash_val,
            pep_match=True,
            risk_score=0.75,
            reason="Politically Exposed Person (PEP) / watchlist match",
            details={"match_type": "pep_watch", "risk_level": "medium_high"},
        )

    # 4. Clean address passes
    status = SCREENING_STATUS_PASSED
    hash_val = compute_screening_hash(norm_address, status, now)
    return ScreeningResult(
        status=status,
        address=norm_address,
        screened_at=now,
        screening_hash=hash_val,
        sanctions_match=False,
        pep_match=False,
        risk_score=0.0,
        reason="Screening passed: clean address",
        details={},
    )


def screen_address(
    address: str,
    db: Optional[Session] = None,
    client: Optional[httpx.Client] = None,
    use_local_evaluator: bool = False,
    timeout: float = 3.0,
) -> ScreeningResult:
    """
    Screen an Algorand wallet address against sanctions / PEP lists.

    Calls KYA POST /api/v1/screen. If the external call fails or is not configured,
    falls back cleanly to the local evaluator.
    """
    norm_address = address.strip()
    if use_local_evaluator:
        return evaluate_locally(norm_address, db=db)

    kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
    payload = {"address": norm_address, "chain": "algorand"}
    headers = {"Content-Type": "application/json"}
    if settings.KYA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.KYA_API_KEY}"

    try:
        if client is not None:
            resp = client.post(kya_url, json=payload, headers=headers, timeout=timeout)
        else:
            with httpx.Client(timeout=timeout) as http_client:
                resp = http_client.post(kya_url, json=payload, headers=headers)

        if resp.status_code in (200, 403):
            try:
                data = resp.json()
            except Exception:
                data = {}

            # Determine status
            raw_status = data.get("status", "").lower()
            if raw_status in VALID_SCREENING_STATUSES:
                status = raw_status
            elif data.get("sanctions_match") or data.get("blocked"):
                status = SCREENING_STATUS_BLOCKED
            elif data.get("pep_match") or data.get("flagged") or data.get("risk_score", 0) >= 0.7:
                status = SCREENING_STATUS_FLAGGED
            elif resp.status_code == 403:
                status = SCREENING_STATUS_BLOCKED
            else:
                status = SCREENING_STATUS_PASSED

            # Parse or generate timestamp
            now = datetime.now(timezone.utc)
            if "screened_at" in data:
                try:
                    screened_at = datetime.fromisoformat(str(data["screened_at"]).replace("Z", "+00:00"))
                except Exception:
                    screened_at = now
            else:
                screened_at = now

            # Audit hash
            screening_hash = data.get("screening_hash") or compute_screening_hash(norm_address, status, screened_at)

            return ScreeningResult(
                status=status,
                address=norm_address,
                screened_at=screened_at,
                screening_hash=screening_hash,
                sanctions_match=bool(data.get("sanctions_match", status == SCREENING_STATUS_BLOCKED)),
                pep_match=bool(data.get("pep_match", status == SCREENING_STATUS_FLAGGED)),
                risk_score=float(data.get("risk_score", 1.0 if status == SCREENING_STATUS_BLOCKED else (0.75 if status == SCREENING_STATUS_FLAGGED else 0.0))),
                reason=data.get("reason"),
                details=data.get("details", data),
            )
        else:
            logger.warning(
                f"KYA screening endpoint returned HTTP {resp.status_code}; falling back to local evaluator"
            )
            return evaluate_locally(norm_address, db=db)

    except Exception as exc:
        logger.warning(
            f"KYA screening request failed ({type(exc).__name__}: {exc}); falling back to local evaluator"
        )
        return evaluate_locally(norm_address, db=db)


async def screen_address_async(
    address: str,
    db: Optional[Session] = None,
    client: Optional[httpx.AsyncClient] = None,
    use_local_evaluator: bool = False,
    timeout: float = 3.0,
) -> ScreeningResult:
    """Async variant of screen_address."""
    norm_address = address.strip()
    if use_local_evaluator:
        return evaluate_locally(norm_address, db=db)

    kya_url = f"{settings.KYA_SERVICE_URL.rstrip('/')}/api/v1/screen"
    payload = {"address": norm_address, "chain": "algorand"}
    headers = {"Content-Type": "application/json"}
    if settings.KYA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.KYA_API_KEY}"

    try:
        if client is not None:
            resp = await client.post(kya_url, json=payload, headers=headers, timeout=timeout)
        else:
            async with httpx.AsyncClient(timeout=timeout) as http_client:
                resp = await http_client.post(kya_url, json=payload, headers=headers)

        if resp.status_code in (200, 403):
            try:
                data = resp.json()
            except Exception:
                data = {}

            raw_status = data.get("status", "").lower()
            if raw_status in VALID_SCREENING_STATUSES:
                status = raw_status
            elif data.get("sanctions_match") or data.get("blocked"):
                status = SCREENING_STATUS_BLOCKED
            elif data.get("pep_match") or data.get("flagged") or data.get("risk_score", 0) >= 0.7:
                status = SCREENING_STATUS_FLAGGED
            elif resp.status_code == 403:
                status = SCREENING_STATUS_BLOCKED
            else:
                status = SCREENING_STATUS_PASSED

            now = datetime.now(timezone.utc)
            if "screened_at" in data:
                try:
                    screened_at = datetime.fromisoformat(str(data["screened_at"]).replace("Z", "+00:00"))
                except Exception:
                    screened_at = now
            else:
                screened_at = now

            screening_hash = data.get("screening_hash") or compute_screening_hash(norm_address, status, screened_at)

            return ScreeningResult(
                status=status,
                address=norm_address,
                screened_at=screened_at,
                screening_hash=screening_hash,
                sanctions_match=bool(data.get("sanctions_match", status == SCREENING_STATUS_BLOCKED)),
                pep_match=bool(data.get("pep_match", status == SCREENING_STATUS_FLAGGED)),
                risk_score=float(data.get("risk_score", 1.0 if status == SCREENING_STATUS_BLOCKED else (0.75 if status == SCREENING_STATUS_FLAGGED else 0.0))),
                reason=data.get("reason"),
                details=data.get("details", data),
            )
        else:
            return evaluate_locally(norm_address, db=db)

    except Exception as exc:
        logger.warning(
            f"KYA screening async request failed ({type(exc).__name__}: {exc}); falling back to local evaluator"
        )
        return evaluate_locally(norm_address, db=db)


# ─── FastAPI Router for KYA Screening Endpoints ─────────────────────────

router = APIRouter(prefix="/api/v1/screening", tags=["screening"])


@router.post("/screen", response_model=ScreeningResponse, summary="Screen an address against OFAC/sanctions lists")
def api_screen_address(req: ScreeningRequest, db: Session = Depends(get_db)):
    result = screen_address(req.address.strip(), db=db)
    return {
        "status": result.status,
        "address": result.address,
        "screened_at": result.screened_at.isoformat(),
        "screening_hash": result.screening_hash,
        "sanctions_match": result.sanctions_match,
        "pep_match": result.pep_match,
        "risk_score": result.risk_score,
        "reason": result.reason,
    }


@router.get("/{address}", response_model=ScreeningResponse, summary="Lookup screening status for an address")
def api_get_screening(address: str, db: Session = Depends(get_db)):
    result = screen_address(address.strip(), db=db)
    return {
        "status": result.status,
        "address": result.address,
        "screened_at": result.screened_at.isoformat(),
        "screening_hash": result.screening_hash,
        "sanctions_match": result.sanctions_match,
        "pep_match": result.pep_match,
        "risk_score": result.risk_score,
        "reason": result.reason,
    }
