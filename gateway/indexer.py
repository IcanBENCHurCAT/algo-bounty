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


def read_box_raw_bytes(app_id: int, box_name: str) -> bytes:
    """Read raw bytes of a box value from an escrow app."""
    try:
        import base64
        algod_client = get_algod_client()
        
        # Try application_box_by_name first
        try:
            resp = algod_client.application_box_by_name(app_id, box_name.encode("utf-8"))
            raw_val = resp.get("value")
            if raw_val:
                return base64.b64decode(raw_val)
        except Exception:
            pass

        # Fallback to application_info box entries
        app_info = algod_client.application_info(app_id)
        local_state = app_info.get("apps-local-state", {})
        boxes = local_state.get("box-entries", [])

        # Try base64 and hex encoding of box_name
        name_b64 = base64.b64encode(box_name.encode("utf-8")).decode("utf-8")
        name_hex = box_name.encode("utf-8").hex()

        for box in boxes:
            b_name = box.get("name", "")
            if b_name in (box_name, name_b64, name_hex):
                raw_val = box.get("value", "")
                
                # Check if it looks like a hex string
                is_hex = len(raw_val) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in raw_val)
                if is_hex:
                    try:
                        return bytes.fromhex(raw_val)
                    except Exception:
                        pass
                
                # Try base64
                try:
                    decoded = base64.b64decode(raw_val)
                    try:
                        decoded.decode("utf-8")
                        return decoded
                    except UnicodeDecodeError:
                        if len(decoded) in (8, 32):
                            return decoded
                        return raw_val.encode("utf-8") if isinstance(raw_val, str) else raw_val
                except Exception:
                    return raw_val.encode("utf-8") if isinstance(raw_val, str) else raw_val
        return None
    except Exception as exc:
        print(f"[INDEXER] Box read error: {exc}")
        return None


def read_box_value(app_id: int, box_name: str):
    """Read a specific box value from an escrow app. Returns decoded string or raw bytes if decode fails."""
    val_bytes = read_box_raw_bytes(app_id, box_name)
    if val_bytes is None:
        return None
    try:
        return val_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return val_bytes


def read_box_uint64(app_id: int, box_name: str) -> int:
    """Read a specific box value from an escrow app as uint64."""
    val_bytes = read_box_raw_bytes(app_id, box_name)
    if val_bytes is None or len(val_bytes) != 8:
        return None
    import struct
    return struct.unpack('>Q', val_bytes)[0]


def read_box_address(app_id: int, box_name: str) -> str:
    """Read a specific box value from an escrow app as an Algorand address string."""
    val_bytes = read_box_raw_bytes(app_id, box_name)
    if val_bytes is None or len(val_bytes) != 32:
        return None
    from algosdk.encoding import encode_address
    return encode_address(val_bytes)


def verify_escrow_schema(app_id: int) -> bool:
    """Verify that the application has the expected box keys of an AlgoBounty contract."""
    try:
        algod_client = get_algod_client()
        boxes_resp = algod_client.application_boxes(app_id)
        box_names = [box.get("name") for box in boxes_resp.get("boxes", [])]
        
        import base64
        state_b64 = base64.b64encode(b"state").decode("utf-8")
        bounty_id_b64 = base64.b64encode(b"bounty_id").decode("utf-8")
        
        has_state = False
        has_bounty_id = False
        for name in box_names:
            if name in (b"state", "state", state_b64):
                has_state = True
            if name in (b"bounty_id", "bounty_id", bounty_id_b64):
                has_bounty_id = True
                
        return has_state and has_bounty_id
    except Exception:
        return False



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
