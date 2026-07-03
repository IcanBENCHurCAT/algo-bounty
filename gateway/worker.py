import asyncio
import os
import signal
import base64
from gateway.database import SessionLocal, Bounty, Agent
from gateway.indexer import poll_bounty_events, fetch_app_logs

async def indexer_worker():
    """Standalone worker process to poll Algorand indexer for bounty events."""
    print("[WORKER] Starting standalone indexer polling worker...")
    last_round = 0

    # Handle termination signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    try:
        while not stop_event.is_set():
            try:
                db = SessionLocal()
                try:
                    # 1. Sync general app state from indexer search
                    events = poll_bounty_events(last_round)
                    if events:
                        for event in events:
                            app_id = event.get("app_id")
                            bounty = db.query(Bounty).filter(Bounty.app_id == app_id).first()
                            if bounty:
                                # General sync placeholder
                                pass
                        last_round = max(e.get("round", 0) for e in events)

                    # 2. Sync specific logs for active bounties (HITM, Dispute, Claim Expiry)
                    active_bounties = db.query(Bounty).filter(
                        Bounty.status.in_(["open", "claimed", "submitted", "rejected", "disputed"])
                    ).all()

                    for bounty in active_bounties:
                        if not bounty.app_id:
                            continue

                        logs_list = fetch_app_logs(bounty.app_id, last_round)
                        for log_entry in logs_list:
                            for log_b64 in log_entry["logs"]:
                                log_bytes = base64.b64decode(log_b64)
                                # Handle HITM Auto-Release
                                if log_bytes == b"auto_released_hitm":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "PAYOUT"
                                        # Karma: +3 worker, +2 creator
                                        worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                        if worker: worker.karma += 3
                                        creator = db.query(Agent).filter(Agent.address == bounty.creator).first()
                                        if creator: creator.karma += 2
                                        db.commit()
                                        print(f"[WORKER] Bounty {bounty.bounty_id} auto-released.")

                                # Handle Dispute Timeout Split
                                elif log_bytes == b"dispute_timeout_split":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "SPLIT"
                                        # Karma: -1 both parties
                                        worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                        if worker: worker.karma -= 1
                                        creator = db.query(Agent).filter(Agent.address == bounty.creator).first()
                                        if creator: creator.karma -= 1
                                        db.commit()
                                        print(f"[WORKER] Bounty {bounty.bounty_id} dispute timed out (split).")

                                # Handle Claim Expired
                                elif log_bytes == b"claim_expired":
                                    if bounty.status != "open":
                                        # Penalty: -20 karma for the ghosting worker
                                        worker = db.query(Agent).filter(Agent.address == bounty.worker).first()
                                        if worker: worker.karma -= 20

                                        bounty.status = "open"
                                        bounty.worker = None
                                        bounty.rejection_count = 0
                                        db.commit()
                                        print(f"[WORKER] Bounty {bounty.bounty_id} claim expired. Reopened.")

                            if log_entry["round"] > last_round:
                                last_round = log_entry["round"]
                finally:
                    db.close()
            except Exception as e:
                print(f"[WORKER] Polling error: {e}")

            # Sleep for 10 seconds or until stop_event is set
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass
    except Exception as e:
        print(f"[WORKER] Fatal error: {e}")
    finally:
        print("[WORKER] Indexer polling worker stopped.")

if __name__ == "__main__":
    asyncio.run(indexer_worker())
