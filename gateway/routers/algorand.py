import logging
from ..schemas import AlgorandHealthResponse, AlgorandBalanceResponse, AlgorandAssetHoldersResponse
from fastapi import APIRouter, HTTPException
from ..algod_client import (
    get_account_balance, get_asset_holders,
    health_check as algo_health_check,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/algorand", tags=["algorand"])

@router.get("/health", response_model=AlgorandHealthResponse, summary="Algorand node health", description="Check the connectivity and status of the Algorand node (Algod) and Indexer. Returns detailed network information.")
def algorand_health():
    """Health check for Algorand network."""
    try:
        status = algo_health_check()
        if status.get("algod") and status.get("indexer"):
            return {"status": "healthy", "network": status["network"], "algod": True, "indexer": True}
        if status.get("error"):
            logger.warning("Algorand health check degraded: %s", status.get("error"))
        return {
            "status": "degraded",
            "network": status["network"],
            "algod": status.get("algod"),
            "indexer": status.get("indexer"),
            "error": "Algorand node or indexer unavailable" if status.get("error") else None,
        }
    except Exception:
        logger.exception("Algorand health check failed")
        raise HTTPException(status_code=503, detail="Algorand health check unavailable")


@router.get("/balance/{address}", response_model=AlgorandBalanceResponse, summary="Get wallet balance", description="Retrieve the current ALGO balance and asset holdings for any Algorand wallet address.")
def algorand_balance(address: str):
    """Return ALGO balance for any address."""
    try:
        result = get_account_balance(address)
        if result.get("error"):
            logger.warning("Algorand balance lookup error for %s: %s", address, result["error"])
            return {**result, "error": "Unable to retrieve wallet balance"}
        return result
    except Exception:
        logger.exception("Failed to fetch wallet balance for %s", address)
        raise HTTPException(status_code=500, detail="Failed to retrieve wallet balance")


@router.get("/asset/{asset_id}/holders", response_model=AlgorandAssetHoldersResponse, summary="List asset holders", description="Retrieve a list of all wallet addresses holding a specific Algorand Standard Asset (ASA).")
def algorand_asset_holders(asset_id: int):
    """Get asset holders for an ASA."""
    try:
        result = get_asset_holders(asset_id)
        if result.get("error"):
            logger.warning("Algorand asset holders lookup error for %s: %s", asset_id, result["error"])
            return {**result, "error": "Unable to retrieve asset holders"}
        return result
    except Exception:
        logger.exception("Failed to fetch asset holders for %s", asset_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve asset holders")
