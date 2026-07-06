"""
Algorand Indexer integration for polling escrow events.

Polls the indexer for on-chain state changes related to bounty escrow
contracts and syncs them back to the local database.
"""
from .algod_client import get_indexer_client, get_algod_client
from .config import settings

try:
    from .database import Bounty
except ImportError:
    Bounty = None  # May be used standalone


def poll_bounty_events(last_polled_round: int = 0):
    """
    Poll indexer for app-related changes.

    Returns list of events that may need DB updates.
    Each event dict contains:
      - bounty_id: str
      - app_id: int
      - app_status: str
      - round: int
    """
    try:
        client = get_indexer_client()
    except Exception as exc:
        print(f"[INDEXER] Cannot connect: {exc}")
        return []

    events = []
    try:
        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}
        template_app_id = settings.ESCROW_TEMPLATE_APP_ID
        if template_app_id > 0:
            search_kwargs["application_id"] = template_app_id
        apps_response = client.search_applications(**search_kwargs)
        apps_list = apps_response.get("applications") or apps_response.get("apps") or []
        current_round = apps_response.get("current-round", 0)

        for app in apps_list:
            app_id = app.get("id")
            if app_id is None or app_id == 0:
                continue

            params = app.get("params", {})
            events.append({
                "app_id": app_id,
                "app_status": params.get("approval-program", "unknown"),
                "round": current_round,
            })

    except Exception as exc:
        print(f"[INDEXER] Indexer search error: {exc}")

    return events


def sync_bounty_from_chain(db, bounty_id: str, chain_status: str):
    """Sync DB status from on-chain state."""
    if Bounty is None:
        return None

    try:
        b = db.query(Bounty).filter(Bounty.bounty_id == bounty_id).first()
    except Exception:
        return None

    if b and b.status != chain_status:
        b.status = chain_status
        try:
            db.commit()
            db.refresh(b)
            return b
        except Exception:
            return None

    return None


def get_bounty_app_info(db, app_id):
    """
    Fetch on-chain app info for a specific app ID.
    Returns dict with app status, or None if error.
    """
    if app_id is None or app_id == 0:
        return None

    try:
        algod_client = get_algod_client()
        app_info = algod_client.application_info(app_id)
        params = app_info.get("params", {})

        result = {
            "app_id": app_id,
            "confirmed_round": app_info.get("last-round", 0),
            "approval_program": params.get("approval-program"),
            "state": "escrow_active",
        }

        # Try reading box values for bounty info
        try:
            boxes = app_info.get("apps-local-state", {}).get("box-entries", [])
            for box in boxes:
                key = box.get("name", "")
                value = box.get("value", "")
                result[f"box_{key}"] = value
        except Exception:
            pass

        return result

    except Exception as exc:
        print(f"[INDEXER] Error fetching app {app_id}: {exc}")
        return None


def read_box_value(app_id: int, box_name: str):
    """Read a specific box value from an escrow app. Returns decoded string or None."""
    try:
        algod_client = get_algod_client()
        app_info = algod_client.application_info(app_id)
        local_state = app_info.get("apps-local-state", {})
        boxes = local_state.get("box-entries", [])

        for box in boxes:
            if box.get("name", "") == box_name:
                raw = box.get("value", "")
                try:
                    return bytes.fromhex(raw).decode("utf-8")
                except (ValueError, UnicodeDecodeError):
                    return raw
        return None
    except Exception as exc:
        print(f"[INDEXER] Box read error: {exc}")
        return None


def fetch_app_logs(app_id: int, min_round: int = 0):
    """Fetch transaction logs for a specific application ID from the indexer."""
    try:
        client = get_indexer_client()
        response = client.search_transactions(
            application_id=app_id,
            min_round=min_round,
            txn_type="appl"
        )
        txns = response.get("transactions", [])
        logs = []
        for tx in txns:
            app_call = tx.get("application-transaction", {})
            # Indexer returns logs in the 'logs' field of the transaction
            tx_logs = tx.get("logs", [])
            if tx_logs:
                logs.append({
                    "tx_id": tx.get("id"),
                    "round": tx.get("confirmed-round"),
                    "logs": tx_logs
                })
        return logs
    except Exception as exc:
        print(f"[INDEXER] Error fetching logs for app {app_id}: {exc}")
        return []
