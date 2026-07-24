import sys
import os
import time
import json
import jwt

# Set root PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gateway.database import SessionLocal, init_db, Bounty, Agent

SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_12345")

def seed():
    init_db()
    db = SessionLocal()
    try:
        creator_addr = "CREATOR_ADDRESS_123456789"
        worker_addr = "WORKER_ADDRESS_987654321"

        # Seed agents
        if not db.query(Agent).filter(Agent.address == creator_addr).first():
            db.add(Agent(address=creator_addr, karma=50))
        if not db.query(Agent).filter(Agent.address == worker_addr).first():
            db.add(Agent(address=worker_addr, karma=30))

        # Seed open bounty for Claiming
        b1 = db.query(Bounty).filter(Bounty.bounty_id == "b_1001").first()
        if not b1:
            db.add(Bounty(
                bounty_id="b_1001",
                app_id=1001,
                status="open",
                creator=creator_addr,
                amount=150000000, # 150 ALGO
                asset_id=0,
                is_hitm=True,
                description="Build a Next.js Landing Page & Wallet Verification Hook",
                repo_url="https://github.com/IcanBENCHurCAT/algo-bounty",
                karma_requirement=10,
                treasury_altered=False,
                platform_fee=200,
                hitm_enforced=False
            ))
        else:
            b1.status = "open"
            b1.worker = None

        # Seed claimed bounty for Submitting
        b2 = db.query(Bounty).filter(Bounty.bounty_id == "b_1002").first()
        if not b2:
            db.add(Bounty(
                bounty_id="b_1002",
                app_id=1002,
                status="claimed",
                creator=creator_addr,
                worker=worker_addr,
                amount=250000000, # 250 ALGO
                asset_id=0,
                is_hitm=False,
                description="Refactor Puya Smart Contract Escrow State Machine",
                repo_url="https://github.com/IcanBENCHurCAT/algo-bounty",
                karma_requirement=25,
                treasury_altered=False,
                platform_fee=200,
                hitm_enforced=False
            ))
        else:
            b2.status = "claimed"
            b2.worker = worker_addr

        # Seed submitted bounty for Approving
        b3 = db.query(Bounty).filter(Bounty.bounty_id == "b_1003").first()
        if not b3:
            db.add(Bounty(
                bounty_id="b_1003",
                app_id=1003,
                status="submitted",
                creator=creator_addr,
                worker=worker_addr,
                amount=500000000, # 500 ALGO
                asset_id=0,
                is_hitm=True,
                description="Implement Automated GitHub OIDC Action Verification",
                repo_url="https://github.com/IcanBENCHurCAT/algo-bounty",
                karma_requirement=15,
                treasury_altered=False,
                platform_fee=200,
                hitm_enforced=False
            ))
        else:
            b3.status = "submitted"
            b3.worker = worker_addr

        db.commit()
        print("Successfully seeded demo bounties: b_1001, b_1002, b_1003")

        # Generate valid JWT tokens for Playwright E2E simulation
        now = int(time.time())
        creator_jwt = jwt.encode({"sub": creator_addr, "iat": now, "exp": now + 86400}, SECRET_KEY, algorithm="HS256")
        worker_jwt = jwt.encode({"sub": worker_addr, "iat": now, "exp": now + 86400}, SECRET_KEY, algorithm="HS256")

        session_tokens = {
            "CREATOR": {
                "address": creator_addr,
                "jwt": creator_jwt,
                "role": "CREATOR"
            },
            "WORKER": {
                "address": worker_addr,
                "jwt": worker_jwt,
                "role": "WORKER"
            }
        }

        tokens_file = os.path.join(os.path.dirname(__file__), "..", "dashboard", "session_tokens.json")
        with open(tokens_file, "w", encoding="utf-8") as f:
            json.dump(session_tokens, f, indent=2)
        print(f"Generated valid session tokens at: {tokens_file}")

    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
