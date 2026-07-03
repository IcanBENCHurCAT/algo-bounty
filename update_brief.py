with open('CONTRACTOR-BRIEF.md', 'r') as f:\n    content = f.read()\n\nold = """### File Structure
```
algo-bounty/
├── gateway/                # FastAPI backend
│   ├── main.py             # Main API (32+ endpoints)
│   ├── auth.py             # Wallet signature + JWT
│   ├── database.py         # DB models (re-exports from supabase_migration)
│   ├── supabase_migration.py # DDL, models, Alembic setup
│   ├── algod_client.py     # Algorand client utilities
│   ├── github.py           # GitHub webhook handler
│   ├── rate_limiter.py     # Rate limiting middleware
│   ├── middleware.py        # Security headers, CORS, size limits
│   ├── indexer.py          # On-chain event poller
│   └── migrations/         # Alembic migrations
├── dashboard/              # Next.js frontend (App Router)
│   ├── src/app/            # Pages
│   ├── src/components/     # React components
│   ├── src/hooks/          # useWallet hook
│   ├── src/lib/            # API client, Supabase helpers
│   └── src/utils/supabase/ # Client/middleware/server configs
├── tests/                  # Test suite
├── supabase/               # RLS policies
├── escrow.algo             # Puya/pyTEAL escrow contract (748 lines)
├── v0-v7*.md               # Design documents
├── AGENTS.md               # Agent guide
├── CONTRACTOR-BRIEF.md     # This file
└── README.md               # Project overview
```"""

new = """### File Structure
```
algo-bounty/
├── gateway/                # FastAPI backend (~8,635 lines)
│   ├── main.py             # Main API (768 lines, 32 endpoints)
│   ├── auth.py             # Wallet signature + JWT (68 lines)
│   ├── database.py         # DB models (re-exports)
│   ├── supabase_migration.py # DDL, models, Alembic (399 lines)
│   ├── algod_client.py     # Algorand client utilities (426 lines)
│   ├── github.py           # GitHub webhook handler (307 lines)
│   ├── rate_limiter.py     # Rate limiting middleware (211 lines)
│   ├── middleware.py        # Security headers, CORS, size limits
│   ├── indexer.py          # On-chain event poller
│   ├── migrations/         # Alembic migrations
│   └── .env.template       # Environment variable template
├── dashboard/              # Next.js frontend (31 files)
│   ├── src/app/            # Pages (layout, index, bounties detail)
│   ├── src/components/     # React components (BountyCard, Layout, Wallet, Toast)
│   ├── src/hooks/          # useWallet hook
│   ├── src/lib/            # API client (296 lines)
│   ├── src/utils/supabase/ # Client/middleware/server configs
│   ├── middleware.ts        # Next.js middleware
│   ├── public/             # Static assets
│   └── package.json        # Node deps
├── tests/                  # Test suite (3 files)
│   ├── test_gateway.py
│   ├── test_escrow_mock.py
│   └── test_escrow_contract.py.bak
├── supabase/               # RLS policies (rls_policies.sql)
├── escrow.algo             # Puya/pyTEAL escrow contract (748 lines)
├── v0-rust-chain-autopsy.md
├── v1-teal-escrow-contract.md
├── v2-karma-reputation-system.md
├── v4-dashboard-api.md
├── v5-github-integration.md
├── v6-hitm-design.md
├── v7-handover.md
├── AGENTS.md               # Project-level agent guide
├── CONTRACTOR-BRIEF.md     # This file
├── CORE-PERSONA.md         # Agent persona
├── README.md               # Project overview
└── deploy*.sh              # Deployment scripts
```"""

if old in content:
    content = content.replace(old, new)
    with open('CONTRACTOR-BRIEF.md', 'w') as f:\n        f.write(content)\n    print("Replaced successfully")
else:
    print("Pattern not found!")
    if "### File Structure" in content:
        idx = content.find("### File Structure")
        print("Found '### File Structure' at index", idx)
        print("Next 200 chars:", repr(content[idx:idx+200]))
