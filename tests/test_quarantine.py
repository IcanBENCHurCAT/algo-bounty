import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from gateway.main import app
from gateway.database import Base, Bounty, Agent, AccountQuarantine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gateway.dependencies import get_db
from gateway.auth import get_current_user, is_admin
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

from tests.conftest import override_get_db as default_override_get_db

def override_user():
    return "QUARANTINED_USER_ADDR"

def override_admin():
    return settings.ADMIN_ADDRESS or "ADMIN_WALLET_ADDR"

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    user = Agent(address="QUARANTINED_USER_ADDR", karma=50)
    admin = Agent(address=settings.ADMIN_ADDRESS or "ADMIN_WALLET_ADDR", karma=100)
    
    now = datetime.now(timezone.utc)
    quarantine = AccountQuarantine(
        address="QUARANTINED_USER_ADDR",
        reason="Suspicious post-refund merge activity",
        details="PR merged after creator reclaimed refund",
        quarantined_at=now,
        expires_at=now + timedelta(hours=72),
        status="active"
    )
    
    db.add(user)
    db.add(admin)
    db.add(quarantine)
    db.commit()
    db.close()
    yield
    app.dependency_overrides[get_db] = default_override_get_db
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(is_admin, None)

def test_quarantine_blocks_bounty_creation():
    app.dependency_overrides[get_current_user] = override_user
    res = client.post(
        "/api/v1/bounties",
        json={
            "bounty_id": "b_new_quarantined",
            "amount": 100,
            "description": "Test bounty",
            "repo_url": "https://github.com/test/repo"
        }
    )
    assert res.status_code == 403
    assert "quarantined" in res.json()["detail"].lower()

def test_quarantine_status_endpoint():
    app.dependency_overrides[get_current_user] = override_user
    res = client.get("/api/v1/bounties/account/quarantine-status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_quarantined"] == True
    assert data["address"] == "QUARANTINED_USER_ADDR"
    assert "Suspicious" in data["reason"]

def test_admin_clear_quarantine():
    app.dependency_overrides[is_admin] = override_admin
    res = client.post(
        "/api/v1/admin/quarantines/1/resolve",
        json={"action": "clear", "resolution_note": "Legitimate agreement verified"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cleared"
    
    # Now user should be able to create bounty (or check status)
    app.dependency_overrides.pop(is_admin, None)
    app.dependency_overrides[get_current_user] = override_user
    status_res = client.get("/api/v1/bounties/account/quarantine-status")
    assert status_res.json()["is_quarantined"] == False
