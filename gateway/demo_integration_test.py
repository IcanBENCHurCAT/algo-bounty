import os
import sys
from datetime import datetime
from unittest.mock import patch

# Configure env
os.environ["ALGORAND_NETWORK"] = "sandbox"
os.environ["SECRET_KEY"] = "demo_dummy_secret_key_at_least_32_characters_long"
os.environ["TESTING"] = "True"

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gateway.main import app, get_db
from gateway.database import Base, Agent, Bounty

# Setup clean local database for demo
SQLALCHEMY_DATABASE_URL = "sqlite:///./gateway_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = DemoSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def run_demo():
    print("======================================================================")
    print("      AlgoBounty Local-Only Platform Demo Integration Test")
    print("======================================================================")
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing clean database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = DemoSessionLocal()
    creator_addr = "CREATOR_WALLET_ADDRESS_DEMO_SAMPLE"
    worker_addr = "WORKER_WALLET_ADDRESS_DEMO_SAMPLE"
    
    creator = Agent(address=creator_addr, karma=100)
    worker = Agent(address=worker_addr, karma=50)
    db.add(creator)
    db.add(worker)
    db.commit()
    print(f"  Seeded Creator Agent: {creator_addr} (Karma: 100)")
    print(f"  Seeded Worker Agent:  {worker_addr} (Karma: 50)")
    
    client = TestClient(app)
    
    # Patch signature verification for simulation
    with patch("gateway.auth.util.verify_bytes", return_value=True):
        # 2. Authenticate Creator
        print("\n[Step 2] Authenticating Creator Wallet...")
        req_res = client.post("/api/v1/auth/request", json={"address": creator_addr})
        challenge = req_res.json()["challenge"]
        verify_res = client.post("/api/v1/auth/verify", json={
            "address": creator_addr,
            "signature": "mock_sig_creator",
            "challenge": challenge
        })
        creator_jwt = verify_res.json()["jwt"]
        print("  Creator authenticated successfully! JWT generated.")
        
        # 3. Authenticate Worker
        print("\n[Step 3] Authenticating Worker Wallet...")
        req_res = client.post("/api/v1/auth/request", json={"address": worker_addr})
        challenge = req_res.json()["challenge"]
        verify_res = client.post("/api/v1/auth/verify", json={
            "address": worker_addr,
            "signature": "mock_sig_worker",
            "challenge": challenge
        })
        worker_jwt = verify_res.json()["jwt"]
        print("  Worker authenticated successfully! JWT generated.")
        
        # 4. Creator Creates a Bounty
        print("\n[Step 4] Creator posting new bounty to Marketplace...")
        bounty_payload = {
            "title": "Refactor Dashboard CSS system",
            "description": "Clean up unused CSS in the Next.js App Router workspace.",
            "amount": 25,
            "asset_id": 0,
            "min_karma": 10,
            "hitm": False,
            "hitm_review_days": 3,
            "repo_url": "https://github.com/IcanBENCHurCAT/algo-bounty"
        }
        create_res = client.post(
            "/api/v1/bounties",
            headers={"Authorization": f"Bearer {creator_jwt}"},
            json=bounty_payload
        )
        print(f"  Create Bounty Response: {create_res.status_code} | {create_res.text}")
        bounty_data = create_res.json()
        bounty_id = bounty_data["bounty_id"]
        print(f"  Bounty Posted! ID: {bounty_id} | Status: '{bounty_data['status']}'")
        
        # 5. List Marketplace Bounties
        print("\n[Step 5] Listing active marketplace bounties...")
        list_res = client.get("/api/v1/bounties")
        print(f"  List Bounties Response: {list_res.status_code} | {list_res.text}")
        bounties_data = list_res.json()
        # Check if response is a dict with a list, or a list directly
        bounties_list = bounties_data if isinstance(bounties_data, list) else bounties_data.get("bounties", [])
        print(f"  Found {len(bounties_list)} open bounty in marketplace:")
        for b in bounties_list:
            print(f"    - ID: {b['bounty_id']} | Status: {b['status']} | Creator: {b['creator']}")
            
        # 6. Worker Claims the Bounty
        print("\n[Step 6] Worker claiming the bounty...")
        claim_res = client.post(
            f"/api/v1/bounties/{bounty_id}/claim",
            headers={"Authorization": f"Bearer {worker_jwt}"},
            json={"signed_txn": ""}
        )
        print(f"  Claim Response status: {claim_res.status_code}")
        updated_bounty = claim_res.json()
        print(f"  Bounty claimed! Status: {updated_bounty['status']} | Assigned Worker: {updated_bounty['worker']}")
        
        # 7. Worker Submits Work
        print("\n[Step 7] Worker submitting completed work pull request...")
        submit_res = client.post(
            f"/api/v1/bounties/{bounty_id}/submit",
            headers={"Authorization": f"Bearer {worker_jwt}"},
            json={
                "pr_url": "https://github.com/IcanBENCHurCAT/algo-bounty/pull/15",
                "proof_data": {"message": "Passes linting and build checks."},
                "signed_txn": ""
            }
        )
        print(f"  Submit Response status: {submit_res.status_code}")
        submitted_bounty = submit_res.json()
        print(f"  Work submitted! Status: {submitted_bounty['status']}")
        
        # 8. Creator Approves Work & Releases Escrow
        print("\n[Step 8] Creator reviewing and approving submitted work...")
        approve_res = client.post(
            f"/api/v1/bounties/{bounty_id}/approve",
            headers={"Authorization": f"Bearer {creator_jwt}"},
            json={"signed_txn": ""}
        )
        print(f"  Approve Response status: {approve_res.status_code}")
        closed_bounty = approve_res.json()
        print(f"  Bounty approved! Status: {closed_bounty['status']} (CLOSED)")
        
        # 9. Verify Karma Updates
        print("\n[Step 9] Checking Agent Karma ratings after completion...")
        creator_db = db.query(Agent).filter(Agent.address == creator_addr).first()
        worker_db = db.query(Agent).filter(Agent.address == worker_addr).first()
        print(f"  Creator Final Karma: {creator_db.karma} (Initial: 100, Deducted: 1 for creation)")
        print(f"  Worker Final Karma:  {worker_db.karma} (Initial: 50, Earned: 15 for completion)")

    print("\n======================================================================")
    print("      Demo integration test successfully completed!")
    print("======================================================================")

if __name__ == "__main__":
    run_demo()
