"""
Algorand client layer -- connects to sandbox (local) or Testnet (production).
Reads credentials from environment variables or Secret Manager secrets.

Tier 1: Sandbox (local dev only) -- 10.0.0.67
Tier 2: Algorand Testnet (production fallback)
Tier 3: Mainnet (future)
"""
import os
import re
import subprocess
from pathlib import Path
from algosdk.v2client import algod, indexer
from algosdk import account
from .config import settings

# --- Tier 1: Sandbox (local dev only) ---
SANDBOX_ALGOD = settings.get_secret("ALGOD_ADDRESS", "http://10.0.0.67:4001")
SANDBOX_TOKEN = settings.get_secret("ALGOD_TOKEN",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
SANDBOX_INDEXER = settings.get_secret("INDEXER_ADDRESS", "http://10.0.0.67:8980")
SANDBOX_INDEXER_TOKEN = settings.get_secret("INDEXER_TOKEN", SANDBOX_TOKEN)

# --- Tier 2: Algorand Testnet (production fallback) ---
TESTNET_ALGOD = settings.get_secret(
    "TESTNET_ALGOD_URL", "https://testnet-api.algonode.cloud"
)
TESTNET_INDEXER = settings.get_secret(
    "TESTNET_INDEXER_URL", "https://testnet-indexer.algonode.cloud"
)
TESTNET_TOKEN = settings.get_secret("TESTNET_ALGOD_TOKEN", "")  # public, no auth

# --- Tier 3: Mainnet (future) ---
MAINNET_ALGOD = settings.get_secret(
    "MAINNET_ALGOD_URL", "https://mainnet-api.algonode.cloud"
)
MAINNET_INDEXER = settings.get_secret(
    "MAINNET_INDEXER_URL", "https://mainnet-indexer.algonode.cloud"
)
MAINNET_TOKEN = settings.get_secret("MAINNET_ALGOD_TOKEN", "")  # public, no auth

# Current active network: sandbox | testnet | mainnet
# Default to testnet for production deployments
NODE_ENV = settings.ALGORAND_NETWORK

# --- Network config lookup ---
_NETWORK_CONFIG = {
    "sandbox": {
        "algod": SANDBOX_ALGOD,
        "indexer": SANDBOX_INDEXER,
        "algod_token": SANDBOX_TOKEN,
        "indexer_token": SANDBOX_INDEXER_TOKEN,
    },
    "testnet": {
        "algod": TESTNET_ALGOD,
        "indexer": TESTNET_INDEXER,
        "algod_token": TESTNET_TOKEN,
        "indexer_token": TESTNET_TOKEN,
    },
    "mainnet": {
        "algod": MAINNET_ALGOD,
        "indexer": MAINNET_INDEXER,
        "algod_token": MAINNET_TOKEN,
        "indexer_token": MAINNET_TOKEN,
    },
}


def _network_cfg():
    """Get config dict for the active network."""
    return _NETWORK_CONFIG.get(NODE_ENV, _NETWORK_CONFIG["testnet"])


# --- Client factories ---

def get_algod_client():
    """Return the Algod client for the active network."""
    cfg = _network_cfg()
    return algod.AlgodClient(cfg["algod_token"], cfg["algod"])


def get_indexer_client():
    """Return the Indexer client for the active network."""
    cfg = _network_cfg()
    return indexer.IndexerClient(cfg["indexer_token"], cfg["indexer"])


def is_sandbox():
    """True when running against the local Algorand sandbox."""
    return NODE_ENV == "sandbox"


def get_default_account():
    """Get the platform's default wallet account."""
    private_key = settings.PLATFORM_PRIVATE_KEY
    if not private_key:
        return None
    return account.from_private_key(private_key)


# --- Health check ---

def health_check():
    """
    Connect to the active network and return status info.

    Returns a dict with:
        - network: active network name
        - algod: bool, algod connectivity
        - algod_info: dict with node version, round, etc. or error
        - indexer: bool, indexer connectivity
        - indexer_info: dict with version/round or error
        - error: str or None
    """
    result = {
        "network": NODE_ENV,
        "algod": False,
        "indexer": False,
        "error": None,
    }
    try:
        ac = get_algod_client()
        info = ac.status()
        result["algod"] = True
        result["algod_info"] = {
            "last_round": info.get("last-round", 0),
            "node_version": info.get("version", ""),
            "network": info.get("network", NODE_ENV),
        }
    except Exception as e:
        result["error"] = str(e)
        return result

    try:
        ic = get_indexer_client()
        info = ic.status()
        result["indexer"] = True
        result["indexer_info"] = {
            "last_round": info.get("last-round", 0),
            "node_version": info.get("version", ""),
        }
    except Exception as e:
        result["indexer"] = False
        if not result.get("error"):
            result["error"] = f"indexer: {e}"

    return result


# --- Account balance ---

def get_account_balance(address):
    """
    Return ALGO balance for an address (microALGO).

    Also returns asset holdings list.
    """
    try:
        ac = get_algod_client()
        info = ac.account_info(address)
        balance = info.get("amount", 0)
        assets = info.get("assets", [])
        return {
            "address": address,
            "balance": balance,
            "balance_algo": balance / 1_000_000,
            "total_assets": len(assets),
            "assets": [
                {"asset_id": a.get("asset-id", 0), "amount": a.get("amount", 0)}
                for a in assets
            ],
        }
    except Exception as e:
        return {
            "address": address,
            "error": str(e),
            "balance": 0,
            "balance_algo": 0,
        }


# --- Transaction status ---

def get_transaction_status(tx_id):
    """
    Look up transaction status via Indexer.

    Returns dict with transaction details or error.
    """
    try:
        ic = get_indexer_client()
        tx_info = ic.transaction_by_id(tx_id)
        return {
            "tx_id": tx_id,
            "confirmed": True,
            "transaction": tx_info,
        }
    except Exception as e:
        # Check if the transaction exists but isn't confirmed yet
        try:
            ic = get_indexer_client()
            pending = ic.pending_transaction_by_id(tx_id)
            return {
                "tx_id": tx_id,
                "confirmed": False,
                "pending": True,
                "transaction": pending,
            }
        except Exception:
            return {
                "tx_id": tx_id,
                "confirmed": False,
                "error": str(e),
            }


# --- Asset holder lookup ---

def get_asset_holders(asset_id):
    """
    Get asset holders for a specific ASA (Algorand Standard Asset).

    Returns list of {address, amount} dicts.
    """
    try:
        # Use account_assets or iterate accounts (limited)
        # Indexer provides /v2/assets/{id}/balances endpoint
        ic = get_indexer_client()
        response = ic.get_asset_balances(asset_id)
        balances = response.get("balances", [])
        holders = [
            {"address": b.get("address", ""), "amount": b.get("amount", 0)}
            for b in balances
            if int(b.get("amount", 0)) > 0  # Exclude zero-balance accounts
        ]
        return {
            "asset_id": asset_id,
            "total_holders": len(holders),
            "holders": holders[:100],  # Limit to first 100
        }
    except Exception as e:
        return {
            "asset_id": asset_id,
            "error": str(e),
            "total_holders": 0,
            "holders": [],
        }


# --- Escrow contract compilation ---

ESCROW_TEAL = None


def compile_escrow_contract():
    """
    Compile escrow.algo -> TEAL bytes.

    Try algokit first (sandbox dev), then fall back to reading a
    pre-compiled .teal file (production / Cloud Run), then strip the
    docstring from the raw Puya source as a last resort.
    """
    global ESCROW_TEAL
    if ESCROW_TEAL is not None:
        return ESCROW_TEAL

    base_dir = Path(__file__).resolve().parent.parent  # algo-bounty/ root
    contract_path = base_dir / "escrow.algo"

    # 1. Try algokit compile
    try:
        result = subprocess.run(
            ["algokit", "compile", str(contract_path), "-o", "/dev/stdout"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            ESCROW_TEAL = result.stdout.strip()
            return ESCROW_TEAL
    except FileNotFoundError:
        pass  # algokit not installed

    # 2. Try pre-compiled .teal (production)
    teal_path = base_dir / "escrow.teal"
    if teal_path.exists():
        try:
            fh = open(teal_path)
            try:
                ESCROW_TEAL = fh.read().strip()
                return ESCROW_TEAL
            finally:
                fh.close()
        except Exception:
            pass

    # 3. Read raw Puya source, strip the docstring block at top
    fh = open(contract_path)
    try:
        content = fh.read()
    finally:
        fh.close()

    # Optimized docstring stripping using regex
    ESCROW_TEAL = re.sub(r'(?s)^.*?[ \t]*(?:"""|\'\'\').*?(?:"""|\'\'\')[^\n]*\r?\n?', '', content, count=1)
    return ESCROW_TEAL


# --- Escrow deployment on testnet ---

def deploy_escrow_on_testnet():
    """
    Full deployment flow for the escrow contract on testnet.

    Steps:
        1. Compile the contract (tries algokit -> .teal -> source strip)
        2. Compile to bytecode via algod
        3. Send ApplicationCreateTxn from platform account
        4. Wait for confirmation and return app_id

    Returns dict with deployment result.
    """
    result = {
        "success": False,
        "app_id": None,
        "tx_id": None,
        "error": None,
    }

    # Must NOT be sandbox
    if is_sandbox():
        result["error"] = "Cannot deploy on sandbox. Set ALGORAND_NETWORK=testnet"
        return result

    # Get platform account
    platform_account = get_default_account()
    if platform_account is None:
        result["error"] = (
            "PLATFORM_PRIVATE_KEY environment variable not set. "
            "Required for contract deployment."
        )
        return result

    try:
        # Step 1: Compile
        teal = compile_escrow_contract()
        if not teal:
            result["error"] = "Failed to compile escrow contract. No TEAL output."
            return result

        # Step 2: Compile to bytecode
        client = get_algod_client()
        compile_resp = client.compile(teal, format="teal")
        compiled_program = compile_resp.get("result", "").encode()

        if not compiled_program:
            result["error"] = "Compiled program is empty"
            return result

        # Step 3: Create deployment transaction
        params = client.suggested_params()
        params.fee = 2000  # Minimum fee
        params.flat_fee = True

        from algosdk.transaction import ApplicationCreateTxn, OnComplete
        create_txn = ApplicationCreateTxn(
            sender=platform_account.address,
            sp=params,
            on_complete=OnComplete.NoOpOC,
            app_args=[],
            program=compiled_program,
            approval_program=compiled_program,
            clear_program=compiled_program,
        )

        # Step 4: Sign and send
        signed_txn = create_txn.sign(platform_account.private_key)
        tx_id = client.send_transaction([signed_txn])
        result["tx_id"] = tx_id

        # Step 5: Wait for confirmation
        from algosdk.waiting import wait_for_confirmation
        pending_info = wait_for_confirmation(client, tx_id, 4)
        if pending_info:
            app_id = pending_info.get("application-index")
            if app_id and app_id > 0:
                result["success"] = True
                result["app_id"] = app_id
                result["network"] = NODE_ENV
                result["message"] = f"Escrow deployed as app #{app_id}"

        return result

    except Exception as e:
        result["error"] = f"Deployment failed: {e}"
        return result


def send_signed_transaction(signed_txn_b64: str):
    """
    Broadcast a base64-encoded signed transaction to the network.
    Returns txid on success.
    """
    import base64

    client = get_algod_client()
    try:
        # Decode base64 signed transaction
        decoded_txn = base64.b64decode(signed_txn_b64)

        # In some cases, the frontend might send a single signed transaction
        # or a list of them. algosdk.v2client.algod.send_transaction expects a list.
        # However, if it's already a single signed transaction, we might need to
        # wrap it in a list or use send_raw_transaction.

        txid = client.send_raw_transaction(decoded_txn)
        return txid
    except Exception as e:
        print(f"[WEB3] Error sending transaction: {e}")
        raise e


# --- ABI type definitions ---
# Note: These are reference strings for documentation.
# The actual contract uses Puya external methods -- deployment is handled
# via ApplicationCreateTxn with the compiled TEAL program.

# Puya contract entry points (as defined in escrow.algo):
#   create_bounty(bounty_id: bytes, escrow_amount: uint64, is_hitm: uint64, asset_id: uint64) void
#   claim_bounty() void
#   submit_work(proof_url: bytes, proof_data: bytes) void
#   approve_work() void
#   reject_work(reason: bytes) void
#   submit_dispute(reason: bytes) void
#   resolve_dispute(resolution: bytes, mediator_signature: bytes) void
#   auto_resolve_creator_win() void
#   timeout_dispute() void
#   auto_release() void
#   claim_abandoned() void
#   expire_claim() void
#   github_verify(pr_url: bytes, test_hash: bytes, oidc_token: bytes) void
#   set_github_status(status: bytes) void
#   get_bounty_info() void
