import sys
import os

# Set root PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gateway.database import SessionLocal, init_db, Bounty, Agent

def seed():
    init_db()
    db = SessionLocal()
    try:
        # Seed test agents
        creator_addr = "CREATOR_ADDRESS_123456789"
        worker_addr = "WORKER_ADDRESS_987654321"

        if not db.query(Agent).filter(Agent.address == creator_addr).first():
            db.add(Agent(address=creator_addr, karma=50))
        if not db.query(Agent).filter(Agent.address == worker_addr).first():
            db.add(Agent(address=worker_addr, karma=30))

        # Check or add open bounty
        if not db.query(Bounty).filter(Bounty.bounty_id == "b_1001").first():
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

        if not db.query(Bounty).filter(Bounty.bounty_id == "b_1002").first():
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

        if not db.query(Bounty).filter(Bounty.bounty_id == "b_1003").first():
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

        db.commit()
        print("Successfully seeded demo bounties: b_1001, b_1002, b_1003")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
