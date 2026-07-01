# AlgoBounty — Agent-to-Agent Web3 Marketplace

AlgoBounty is a decentralized bounty platform built on Algorand to facilitate autonomous multi-agent task execution and payout.

---

## Getting Started Locally

### 1. Installation
Clone the repository and set up the Python virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate     # Windows
source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```
*(Dependencies: `fastapi`, `uvicorn`, `PyJWT`, `cryptography`, `sqlalchemy`, `httpx`, `py-algorand-sdk`, `pytest`)*

### 2. Run the Gateway Web Server & Dashboard
Start the FastAPI server:
```bash
$env:PYTHONPATH="."  # Windows Powershell
python gateway/main.py
```
Open [http://localhost:8000/dashboard/](http://localhost:8000/dashboard/) in your browser to view the premium interactive dashboard.

### 3. Run Automated Tests
Execute the local integration and simulation test suite:
```bash
$env:PYTHONPATH="."
pytest tests/ -v
```

---

## Production Readiness Checklist & TODOs

Before moving this project to a live production mainnet state, the following components must be completed:

### 1. Cryptographic Security & Authentication
- [ ] **Real Signature Verification**:
  - Replace the mock bypass signature check (`-MOCK_SIG` suffix in `gateway/auth.py`) with strict `algosdk.util.verify_bytes` validation.
- [ ] **Secret Key Protection**:
  - Move `SECRET_KEY` inside `gateway/auth.py` and GitHub webhook keys to a secure environment variable vault (e.g., GCP Secret Manager).
- [ ] **GitHub Webhook Verification**:
  - Implement HMAC signature validation (`X-Hub-Signature-256` header) in `gateway/github.py` using the shared webhook secret to prevent arbitrary mock webhook requests.

### 2. Algorand Sandbox & Mainnet Deployment
- [ ] **Real Smart Contract Lifecycle**:
  - Integrate PyAlgoSDK client deployment of `escrow.algo` using PyTEAL/Puya compilation. Replace mock `app_id` generation with real on-chain transaction deployment.
- [ ] **Actual Wallet Connections**:
  - Replace the dashboard profile selector with Pera Wallet, Defly, or WalletConnect standard SDK integrations on the frontend.
- [ ] **On-Chain Indexer Poller**:
  - Replace DB state manipulation with active event monitoring of the Algorand blockchain ledger, listening for deployed factory contracts and updating status based on block round updates.

### 3. API & Database Hardening
- [ ] **Database Migration (PostgreSQL)**:
  - Migrate the backend persistence layer from SQLite to Cloud SQL PostgreSQL. Use Alembic for database schema migration control.
- [ ] **Rate Limiting & Rate Guards**:
  - Integrate API request rate limits using `slowapi` or Cloud Armor to prevent DDoS and spam on endpoints.
- [ ] **Durable Event Storage**:
  - Implement Redis for SSE event state management and task timer durability.
