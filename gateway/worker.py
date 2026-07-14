import asyncio
import os
import signal
import base64
from datetime import datetime, timezone
from gateway.database import SessionLocal, Bounty, Agent, Arbitrator, DisputeArbitrator
from gateway.indexer import poll_bounty_events, fetch_app_logs, read_box_value, sync_bounty_from_chain

async def indexer_worker():
    """Standalone worker process to poll Algorand indexer for bounty events."""
    print("[WORKER] Starting standalone indexer polling worker...")
    last_round = 0

    # Handle termination signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
    except NotImplementedError:
        # Windows fallback: loop.add_signal_handler is not implemented
        def sync_handler(signum, frame):
            loop.call_soon_threadsafe(stop_event.set)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, sync_handler)

    try:
        while not stop_event.is_set():
            try:
                db = SessionLocal()
                try:
                    # 1. Sync general app state from indexer search
                    events = poll_bounty_events(last_round)
                    if events:
                        app_ids = [event.get("app_id") for event in events if event.get("app_id")]
                        bounties = db.query(Bounty).filter(Bounty.app_id.in_(app_ids)).all()
                        bounty_map = {b.app_id: b for b in bounties}
                        for event in events:
                            app_id = event.get("app_id")
                            bounty = bounty_map.get(app_id)
                            if bounty:
                                # General sync placeholder
                                try:
                                    state_raw = read_box_value(app_id, "state")
                                    if state_raw:
                                        import struct
                                        # read_box_value might return the raw string if decode failed
                                        # But let's safely decode hex if needed
                                        if isinstance(state_raw, str):
                                            try:
                                                state_bytes = bytes.fromhex(state_raw)
                                            except ValueError:
                                                state_bytes = state_raw.encode('utf-8')
                                        else:
                                            state_bytes = state_raw

                                        if len(state_bytes) == 8:
                                            state_int = struct.unpack('>Q', state_bytes)[0]

                                            state_map = {
                                                0: "open",
                                                1: "claimed",
                                                2: "submitted",
                                                3: "rejected",
                                                4: "disputed",
                                                5: "closed",
                                                6: "closed",  # split
                                                7: "open"     # claim expired
                                            }

                                            new_status = state_map.get(state_int)
                                            if new_status and bounty.status != new_status:
                                                sync_bounty_from_chain(db, bounty.bounty_id, new_status)
                                                print(f"[WORKER] Synced bounty {bounty.bounty_id} state to {new_status}")
                                except Exception as e:
                                    print(f"[WORKER] Error syncing general state for {bounty.bounty_id}: {e}")
                        last_round = max(e.get("round", 0) for e in events)

                    # 2. Sync specific logs for active bounties (HITM, Dispute, Claim Expiry)
                    active_bounties = db.query(Bounty).filter(
                        Bounty.status.in_(["open", "claimed", "submitted", "rejected", "disputed"])
                    ).all()

                    # Pre-fetch agents to avoid N+1 queries
                    relevant_addresses = set()
                    for b in active_bounties:
                        if b.worker:
                            relevant_addresses.add(b.worker)
                        if b.creator:
                            relevant_addresses.add(b.creator)

                    agents_by_address = {}
                    if relevant_addresses:
                        agents = db.query(Agent).filter(Agent.address.in_(relevant_addresses)).all()
                        agents_by_address = {a.address: a for a in agents}

                    changes_made = False
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
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker: worker.karma += 3
                                        creator = agents_by_address.get(bounty.creator)
                                        if creator: creator.karma += 2
                                        changes_made = True
                                        print(f"[WORKER] Bounty {bounty.bounty_id} auto-released.")

                                # Handle Dispute Timeout Split
                                elif log_bytes == b"dispute_timeout_split":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "SPLIT"
                                        # Karma: -1 both parties
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker: worker.karma -= 1
                                        creator = agents_by_address.get(bounty.creator)
                                        if creator: creator.karma -= 1
                                        changes_made = True
                                        print(f"[WORKER] Bounty {bounty.bounty_id} dispute timed out (split).")

                                # Handle Claim Expired
                                elif log_bytes == b"claim_expired":
                                    if bounty.status != "open":
                                        # Penalty: -20 karma for the ghosting worker
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker: worker.karma -= 20

                                        bounty.status = "open"
                                        bounty.worker = None
                                        bounty.rejection_count = 0
                                        changes_made = True
                                        print(f"[WORKER] Bounty {bounty.bounty_id} claim expired. Reopened.")

                                # Handle Dispute Submitted and Arbitrator Selection
                                elif log_bytes == b"dispute_submitted":
                                    from algosdk.encoding import encode_address
                                    logs_in_tx = log_entry["logs"]
                                    idx_in_tx = log_entry["logs"].index(log_b64)
                                    if idx_in_tx + 3 < len(logs_in_tx):
                                        arb1_bytes = base64.b64decode(logs_in_tx[idx_in_tx + 1])
                                        arb2_bytes = base64.b64decode(logs_in_tx[idx_in_tx + 2])
                                        arb3_bytes = base64.b64decode(logs_in_tx[idx_in_tx + 3])
                                        
                                        arb1_addr = encode_address(arb1_bytes)
                                        arb2_addr = encode_address(arb2_bytes)
                                        arb3_addr = encode_address(arb3_bytes)
                                        
                                        bounty.status = "disputed"
                                        
                                        # Ensure they exist in DB and update assignment
                                        for addr in [arb1_addr, arb2_addr, arb3_addr]:
                                            if not db.query(Arbitrator).filter(Arbitrator.address == addr).first():
                                                db.add(Arbitrator(address=addr, status="active"))
                                            
                                            assignment = db.query(DisputeArbitrator).filter(
                                                DisputeArbitrator.bounty_id == bounty.bounty_id,
                                                DisputeArbitrator.arbitrator_address == addr
                                            ).first()
                                            if not assignment:
                                                db.add(DisputeArbitrator(bounty_id=bounty.bounty_id, arbitrator_address=addr))
                                        
                                        changes_made = True
                                        print(f"[WORKER] Bounty {bounty.bounty_id} disputed. Assigned: {arb1_addr}, {arb2_addr}, {arb3_addr}")

                                # Handle Arbitrator Voted
                                elif log_bytes == b"arbitrator_voted":
                                    from algosdk.encoding import encode_address
                                    import struct
                                    logs_in_tx = log_entry["logs"]
                                    idx_in_tx = log_entry["logs"].index(log_b64)
                                    if idx_in_tx + 2 < len(logs_in_tx):
                                        voter_bytes = base64.b64decode(logs_in_tx[idx_in_tx + 1])
                                        voter_addr = encode_address(voter_bytes)
                                        
                                        vote_opt_bytes = base64.b64decode(logs_in_tx[idx_in_tx + 2])
                                        vote_opt_val = struct.unpack('>Q', vote_opt_bytes)[0]
                                        
                                        vote_map = {1: "worker", 2: "payer", 3: "split"}
                                        vote_str = vote_map.get(vote_opt_val)
                                        
                                        if vote_str:
                                            assignment = db.query(DisputeArbitrator).filter(
                                                DisputeArbitrator.bounty_id == bounty.bounty_id,
                                                DisputeArbitrator.arbitrator_address == voter_addr
                                            ).first()
                                            if assignment and assignment.vote is None:
                                                assignment.vote = vote_str
                                                assignment.voted_at = datetime.now(timezone.utc)
                                                changes_made = True
                                                print(f"[WORKER] Arbitrator {voter_addr} voted {vote_str} on {bounty.bounty_id}")

                                # Handle Dispute Resolved Win/Loss/Split
                                elif log_bytes == b"dispute_resolved_agent_win":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "PAYOUT"
                                        
                                        # Karma: +5 worker, -5 creator
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker:
                                            worker.karma += 5
                                            worker.completed_bounties += 1
                                        creator = agents_by_address.get(bounty.creator)
                                        if creator:
                                            creator.karma -= 5
                                            creator.disputes_lost += 1
                                        changes_made = True
                                        print(f"[WORKER] Dispute on bounty {bounty.bounty_id} resolved in favor of worker.")

                                elif log_bytes == b"dispute_resolved_creator_win":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "REFUND"
                                        
                                        # Karma: +5 creator, -5 worker
                                        creator = agents_by_address.get(bounty.creator)
                                        if creator:
                                            creator.karma += 5
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker:
                                            worker.karma -= 5
                                            worker.disputes_lost += 1
                                        changes_made = True
                                        print(f"[WORKER] Dispute on bounty {bounty.bounty_id} resolved in favor of creator.")

                                elif log_bytes == b"dispute_resolved_split":
                                    if bounty.status != "closed":
                                        bounty.status = "closed"
                                        bounty.payout_type = "SPLIT"
                                        # Karma: No karma changes for split (already penalized or neutral)
                                        # Increment completed_bounties for worker as they did some work
                                        worker = agents_by_address.get(bounty.worker)
                                        if worker:
                                            worker.completed_bounties += 1
                                        changes_made = True
                                        print(f"[WORKER] Dispute on bounty {bounty.bounty_id} resolved with a split payout.")

                            if log_entry["round"] > last_round:
                                last_round = log_entry["round"]

                    if changes_made:
                        db.commit()
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

from fastapi import FastAPI
import uvicorn

worker_app = FastAPI(title="AlgoBounty Indexer Worker")

@worker_app.get("/health")
def health():
    return {"status": "ok", "message": "Indexer worker is active."}

@worker_app.on_event("startup")
async def startup_event():
    asyncio.create_task(indexer_worker())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(worker_app, host="0.0.0.0", port=port)
