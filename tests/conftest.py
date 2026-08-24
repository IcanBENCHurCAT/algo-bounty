import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# Set environment before importing gateway modules
os.environ["ALGORAND_NETWORK"] = "sandbox"
os.environ["SECRET_KEY"] = "test_dummy_secret_key_at_least_32_characters_long"
os.environ["TESTING"] = "True"

from gateway.dependencies import get_db
from gateway.main import app
from gateway.database import Base, Agent

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_all.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean_db():
    db = TestingSessionLocal()
    try:
        if 'dispute_evaluators' in Base.metadata.tables:
            db.execute(Base.metadata.tables['dispute_evaluators'].delete())
        if 'dispute_arbitrators' in Base.metadata.tables:
            db.execute(Base.metadata.tables['dispute_arbitrators'].delete())
        if 'notifications' in Base.metadata.tables:
            db.execute(Base.metadata.tables['notifications'].delete())
        if 'github_prs' in Base.metadata.tables:
            db.execute(Base.metadata.tables['github_prs'].delete())
        if 'bounties' in Base.metadata.tables:
            db.execute(Base.metadata.tables['bounties'].delete())
        if 'evaluators' in Base.metadata.tables:
            db.execute(Base.metadata.tables['evaluators'].delete())
        if 'arbitrators' in Base.metadata.tables:
            db.execute(Base.metadata.tables['arbitrators'].delete())
        if 'account_quarantines' in Base.metadata.tables:
            db.execute(Base.metadata.tables['account_quarantines'].delete())
        if 'sync_records' in Base.metadata.tables:
            db.execute(Base.metadata.tables['sync_records'].delete())
        if 'agents' in Base.metadata.tables:
            db.execute(Base.metadata.tables['agents'].delete())
        if 'webhook_delivery_records' in Base.metadata.tables:
            db.execute(Base.metadata.tables['webhook_delivery_records'].delete())
        db.commit()
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def seeded_agents(db_session):
    creator = Agent(address="CREATOR_ADDR", karma=50)
    worker = Agent(address="WORKER_ADDR", karma=30)
    low_karma_worker = Agent(address="LOW_KARMA_WORKER", karma=5)
    db_session.add(creator)
    db_session.add(worker)
    db_session.add(low_karma_worker)
    db_session.commit()
    return creator, worker, low_karma_worker

def get_auth_token(client, address: str) -> str:
    res = client.post("/api/v1/auth/request", json={"address": address})
    if res.status_code != 200:
        print(f"Auth request failed: {res.text}")
    challenge = res.json()["challenge"]
    with patch("gateway.auth.util.verify_bytes", return_value=True):
        verify_res = client.post("/api/v1/auth/verify", json={
            "address": address,
            "signature": "fake_signature",
            "challenge": challenge
        })
        if verify_res.status_code != 200:
            print(f"Auth verify failed: {verify_res.text}")
        return verify_res.json()["jwt"]
