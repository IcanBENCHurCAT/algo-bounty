import asyncio
import os
import signal
from gateway.database import SessionLocal, Bounty
from gateway.indexer import poll_bounty_events

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
                events = poll_bounty_events(last_round)
                if events:
                    db = SessionLocal()
                    try:
                        for event in events:
                            app_id = event.get("app_id")
                            # In a more complete implementation, we'd fetch the full app state
                            # and determine the corresponding DB status.
                            # For now, we'll use a placeholder sync call.
                            bounty = db.query(Bounty).filter(Bounty.app_id == app_id).first()
                            if bounty:
                                # Example: sync_bounty_from_chain(db, bounty.bounty_id, "active")
                                pass

                        if events:
                            last_round = max(e.get("round", 0) for e in events)
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
