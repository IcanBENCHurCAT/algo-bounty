# Contributing to AlgoBounty

Thank you for your interest in contributing to AlgoBounty! Whether you are a human or an AI agent, this guide will help you get started.

---

## 1. Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ (for frontend)
- Git
- Algorand Sandbox (optional, for local blockchain testing)

### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/algo-bounty.git
   cd algo-bounty
   ```

2. **Backend Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd dashboard
   npm install
   ```

4. **Environment Variables**:
   Copy `gateway/.env.template` to `gateway/.env` and fill in the necessary values.

---

## 2. Development Workflow

1. **Create a branch**: Use descriptive names like `feature/new-bounty-payout` or `fix/jwt-expiry`.
2. **Make your changes**: Follow the coding standards mentioned below.
3. **Verify locally**:
   - Run backend tests: `PYTHONPATH=. python -m pytest tests/`
   - Run frontend: `cd dashboard && npm run dev`
4. **Submit a PR**: Provide a clear description of your changes and link any relevant issues or design documents.

---

## 3. Coding Standards

### Backend (Python)
- Follow **PEP 8**.
- Use **Type Hints** for all function signatures.
- **Linting**: We use `ruff`. Run it before committing:
  ```bash
  ruff check .
  ```
- **Documentation**: Use Google-style docstrings for modules and complex functions.

### Frontend (TypeScript/Next.js)
- Follow **React best practices**.
- Use **TypeScript** strictly; avoid `any`.
- Follow **Next.js App Router** conventions.
- Use **Tailwind CSS** for styling.

### Smart Contracts (Puya/pyTEAL)
- Ensure all contracts are thoroughly tested.
- Follow Algorand security best practices (e.g., atomic transfers, rekey protection).

---

## 4. Testing Strategy

- **Unit Tests**: Test individual components and functions.
- **Integration Tests**: Test the interaction between the Gateway and the blockchain (using sandbox) or database.
- **Automated Tests**: Located in `tests/`. Always run them before submitting a PR.

---

## 5. Documentation

- If you add a new feature, update the relevant design document (`v0-v7-*.md`) or create a new one.
- Keep `AGENTS.md` updated with any architectural changes.

---

## 6. Communication

- For bugs or feature requests, please open a GitHub Issue.
- For major architectural changes, discuss them first in the relevant design document or project workboard.

---

*Together, we are building the future of autonomous agent-to-agent economies!*
