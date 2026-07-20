from ..schemas import AlgorandHealthResponse, AlgorandBalanceResponse, AlgorandAssetHoldersResponse
from fastapi import APIRouter, HTTPException
from ..algod_client import (
    get_account_balance, get_asset_holders,
    health_check as algo_health_check,
)

router = APIRouter(prefix="/api/v1/algorand", tags=["algorand"])

@router.get("/health", response_model=AlgorandHealthResponse, summary="Algorand node health", description="Check the connectivity and status of the Algorand node (Algod) and Indexer. Returns detailed network information.")
def algorand_health():
    """Health check for Algorand network."""
    try:
        status = algo_health_check()
        if status.get("algod") and status.get("indexer"):
            return {"status": "healthy", "network": status["network"], "algod": True, "indexer": True}
        return {"status": "degraded", "network": status["network"], "algod": status.get("algod"), "indexer": status.get("indexer"), "error": status.get("error")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/balance/{address}", response_model=AlgorandBalanceResponse, summary="Get wallet balance", description="Retrieve the current ALGO balance and asset holdings for any Algorand wallet address.")
def algorand_balance(address: str):
    """Return ALGO balance for any address."""
    try:
        return get_account_balance(address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/asset/{asset_id}/holders", response_model=AlgorandAssetHoldersResponse, summary="List asset holders", description="Retrieve a list of all wallet addresses holding a specific Algorand Standard Asset (ASA).")
def algorand_asset_holders(asset_id: int):
    """Get asset holders for an ASA."""
    try:
        return get_asset_holders(asset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
