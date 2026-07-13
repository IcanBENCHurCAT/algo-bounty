import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gateway.database import Base, Bounty

# Setup in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def setup_db():
    db = TestingSessionLocal()
    # Create 500 bounties
    for i in range(500):
        b = Bounty(
            bounty_id=f"bounty_{i}",
            app_id=1000 + i,
            creator="creator_addr",
            amount=100,
            repo_url="https://github.com/test/test"
        )
        db.add(b)
    db.commit()
    db.close()

def mock_events():
    return [{"app_id": 1000 + i, "round": 10} for i in range(500)]

def run_old_loop():
    db = TestingSessionLocal()
    events = mock_events()
    start_time = time.time()

    # Old logic
    if events:
        for event in events:
            app_id = event.get("app_id")
            bounty = db.query(Bounty).filter(Bounty.app_id == app_id).first()
            if bounty:
                pass # placeholder

    end_time = time.time()
    db.close()
    return end_time - start_time

def run_new_loop():
    db = TestingSessionLocal()
    events = mock_events()
    start_time = time.time()

    # New logic
    if events:
        app_ids = [event.get("app_id") for event in events if event.get("app_id")]
        bounties = db.query(Bounty).filter(Bounty.app_id.in_(app_ids)).all()
        bounty_map = {b.app_id: b for b in bounties}
        for event in events:
            app_id = event.get("app_id")
            bounty = bounty_map.get(app_id)
            if bounty:
                pass # placeholder

    end_time = time.time()
    db.close()
    return end_time - start_time


if __name__ == "__main__":
    setup_db()

    print("Running old loop...")
    old_time = run_old_loop()
    print(f"Old loop took: {old_time:.4f} seconds")

    print("Running new loop (for comparison)...")
    new_time = run_new_loop()
    print(f"New loop took: {new_time:.4f} seconds")
