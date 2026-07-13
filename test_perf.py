import time
import asyncio
import os
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gateway.database import Base
from gateway.supabase_migration import Agent, Bounty, GitHubPR
from gateway.github import handle_pr_event

os.environ["GITHUB_TOKEN"] = "mock_token"

engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def setup_db():
    db = SessionLocal()
    # Create an agent
    author = "testuser"
    agent = Agent(address=author, karma=0, completed_bounties=0)
    db.add(agent)

    # Create 100 bounties linked to PRs
    for i in range(100):
        bounty = Bounty(bounty_id=f"b_{i}", status="claimed", worker=author, is_hitm=False, repo_url="testrepo", creator="creator", amount=10)
        db.add(bounty)
    db.commit()
    return db

async def measure():
    db = setup_db()

    # Simulate a PR event closing 100 bounties
    payload = {
        "action": "closed",
        "pull_request": {
            "title": "Fixes " + " ".join([f"#ALGO-{i}" for i in range(100)]),
            "number": 1,
            "user": {"login": "testuser"},
            "merged": True
        },
        "repository": {"html_url": "testrepo"}
    }

    start_time = time.time()

    # Mock post_github_comment_and_labels to avoid hitting github API
    with patch("gateway.github.post_github_comment_and_labels") as mock_post:
        await handle_pr_event(db, payload)

    end_time = time.time()

    print(f"Time taken: {end_time - start_time} seconds")

if __name__ == "__main__":
    asyncio.run(measure())
