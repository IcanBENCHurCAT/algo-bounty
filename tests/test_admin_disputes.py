import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from gateway.main import app
from gateway.database import Base, Bounty, Agent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gateway.dependencies import get_db
from gateway.auth import get_current_user
from gateway.config import settings

engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_admin():
    return settings.ADMIN_ADDRESS or "ADMIN_WALLET_ADDR"

def override_user():
    return "NON_ADMIN_WALLET_ADDR"

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    old_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    admin_addr = settings.ADMIN_ADDRESS or "ADMIN_WALLET_ADDR"
    admin = Agent(address=admin_addr, karma=100)
    user = Agent(address="NON_ADMIN_WALLET_ADDR", karma=10)
    worker = Agent(address="WORKER_ADDR", karma=10)
    bounty = Bounty(
        bounty_id="ALGO-DISPUTE-1",
        creator="NON_ADMIN_WALLET_ADDR",
        worker="WORKER_ADDR",
        status="disputed",
        amount=500,
        repo_url="https://github.com/test/repo"
    )
    db.add(admin)
    db.add(user)
    db.add(worker)
    db.add(bounty)
    db.commit()
    db.close()
    yield
    app.dependency_overrides = old_overrides

from gateway.auth import get_current_user, is_admin

def test_admin_resolve_dispute_worker_win():
    app.dependency_overrides[is_admin] = override_admin
    res = client.post(
        "/api/v1/admin/disputes/ALGO-DISPUTE-1/resolve",
        json={"resolution": "worker_win", "reason": "Work verified by admin"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "resolved"
    assert data["resolution"] == "worker_win"
    
    db = TestingSessionLocal()
    bounty = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-DISPUTE-1").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "PAYOUT"
    db.close()

def test_admin_resolve_dispute_creator_win():
    app.dependency_overrides[is_admin] = override_admin
    res = client.post(
        "/api/v1/admin/disputes/ALGO-DISPUTE-1/resolve",
        json={"resolution": "creator_win", "reason": "Work invalid"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "resolved"
    assert data["resolution"] == "creator_win"
    
    db = TestingSessionLocal()
    bounty = db.query(Bounty).filter(Bounty.bounty_id == "ALGO-DISPUTE-1").first()
    assert bounty.status == "closed"
    assert bounty.payout_type == "REFUND"
    db.close()

def test_admin_resolve_non_admin_rejected():
    app.dependency_overrides.pop(is_admin, None)
    app.dependency_overrides[get_current_user] = override_user
    res = client.post(
        "/api/v1/admin/disputes/ALGO-DISPUTE-1/resolve",
        json={"resolution": "worker_win"}
    )
    assert res.status_code == 403
    assert "Administrator access required" in res.json()["detail"]
