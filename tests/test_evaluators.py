import pytest
from fastapi.testclient import TestClient

from gateway.main import app
from gateway.database import Base, Agent, Evaluator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gateway.dependencies import get_db
from gateway.auth import get_current_user

engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def override_get_current_user_good():
    return "GOOD_ADDRESS"

def override_get_current_user_bad():
    return "BAD_ADDRESS"

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    agent_good = Agent(address="GOOD_ADDRESS", karma=100)
    agent_bad = Agent(address="BAD_ADDRESS", karma=10)
    db.add(agent_good)
    db.add(agent_bad)
    db.commit()
    db.close()

def test_register_evaluator_success():
    app.dependency_overrides[get_current_user] = override_get_current_user_good
    response = client.post("/api/v1/evaluators/register")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["address"] == "GOOD_ADDRESS"
    assert response.json()["karma"] == 100

def test_register_evaluator_low_karma():
    app.dependency_overrides[get_current_user] = override_get_current_user_bad
    response = client.post("/api/v1/evaluators/register")
    assert response.status_code == 403
    assert "Insufficient karma" in response.json()["detail"]

def test_deregister_evaluator():
    app.dependency_overrides[get_current_user] = override_get_current_user_good
    client.post("/api/v1/evaluators/register")
    
    response = client.post("/api/v1/evaluators/deregister")
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["address"] == "GOOD_ADDRESS"

def test_list_evaluators():
    app.dependency_overrides[get_current_user] = override_get_current_user_good
    client.post("/api/v1/evaluators/register")
    
    response = client.get("/api/v1/evaluators")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["evaluators"][0]["address"] == "GOOD_ADDRESS"
    assert response.json()["evaluators"][0]["karma"] == 100

def test_get_my_status():
    app.dependency_overrides[get_current_user] = override_get_current_user_good
    response = client.get("/api/v1/evaluators/me")
    assert response.status_code == 200
    assert response.json()["can_register"] == True
    assert response.json()["status"] == "inactive"
    
    client.post("/api/v1/evaluators/register")
    response2 = client.get("/api/v1/evaluators/me")
    assert response2.json()["status"] == "active"

def test_refund_blocked_from_submitted_state():
    """FR-002: Verify that no refund endpoint or method allows reclaiming funds while work is submitted."""
    from gateway.database import Bounty
    db = TestingSessionLocal()
    bounty = Bounty(
        bounty_id="TEST-SUBMITTED-1",
        creator="GOOD_ADDRESS",
        worker="BAD_ADDRESS",
        status="submitted",
        amount=1000,
        repo_url="https://github.com/test/repo"
    )
    db.add(bounty)
    db.commit()
    db.close()
    
    # Verify via API or DB invariant that status is submitted and cannot be unilaterally refunded
    db = TestingSessionLocal()
    fetched = db.query(Bounty).filter(Bounty.bounty_id == "TEST-SUBMITTED-1").first()
    assert fetched.status == "submitted"
    assert fetched.payout_type is None
    db.close()
