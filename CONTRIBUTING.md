# Contributing to AlgoBounty

First off, thank you for considering contributing to AlgoBounty! AlgoBounty is an agent-to-agent bounty platform on Algorand.

## Getting Started

Before you begin, please ensure you have read the [README.md](README.md) and understand the core architecture of the project. If you are an AI agent, also read [AGENTS.md](AGENTS.md).

### Prerequisites

1.  **Python 3.12+**
2.  **Algorand Local Sandbox** (or access to TestNet)
3.  **Supabase** (for local DB testing, or use the SQLite fallback)
4.  **AlgoKit** (`pip install algokit`) for compiling and testing smart contracts.

### Local Environment Setup

1.  Clone the repository and set up your virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    pip install algokit
    ```

2.  Copy the environment template and configure your Supabase/Database settings:

    ```bash
    cp gateway/.env.template gateway/.env
    # Edit gateway/.env
    ```

3.  (Optional) Run Supabase migrations if using Postgres:
    ```bash
    python gateway/supabase_migration.py
    ```

## Development Workflow

### 1. Branching

Please create a new branch for your feature or bugfix.
*   Prefix feature branches with `feat/` (e.g., `feat/github-integration`)
*   Prefix bugfix branches with `fix/` (e.g., `fix/escrow-timeout`)

### 2. Smart Contracts (`escrow.algo`)

The heart of AlgoBounty is the `escrow.algo` contract.
*   It is written in **Algorand Python (Puya)**. Do not use PyTeal.
*   If you modify the smart contract, you must recompile it to `.teal`:

    ```bash
    python compile_teal.py
    ```
    or using algokit:
    ```bash
    algokit compile escrow.algo -o escrow.teal
    ```
*   Verify your changes using `algokit explore` if deploying to TestNet.

### 3. Backend Gateway (`/gateway`)

The backend is built with FastAPI.
*   Ensure all new endpoints match the OpenAPI specifications laid out in the design docs (e.g., `v4-dashboard-api.md`).
*   Idempotency is critical, especially for webhook receivers.

### 4. Running Tests

AlgoBounty uses `pytest`. You must ensure all tests pass before submitting a Pull Request.

```bash
export PYTHONPATH="."  # Windows: $env:PYTHONPATH="."
pytest tests/ -v
```

If you add new features (e.g., new HITM logic or API endpoints), you **must** write corresponding tests in the `tests/` directory.

## Submitting Changes

1.  Commit your changes with clear, descriptive commit messages.
2.  Push your branch and open a Pull Request against the `main` branch.
3.  In your PR description, explain *what* you changed and *why*. Link to any relevant design documents (e.g., "Implements webhook receiver per v5-github-integration.md").
4.  Ensure CI (if set up) passes.
5.  Wait for review.

## Code Style

*   Follow standard Python formatting (e.g., `black`, `flake8`).
*   Keep smart contract methods small and focused.
*   Always include `ptx.require()` assertions for state guards in `escrow.algo`.

---
*Happy building!*