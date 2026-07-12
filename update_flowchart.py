import re

old_block = """┌──────────────────────────────────────────────────────────────┐
│                       ALGOBOUNTY PLATFORM                      │
│                                                                │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────┐ │
│  │  Next.js     │    │  FastAPI Gateway │    │ Indexer     │ │
│  │  Dashboard   │◄──►│  (REST + SSE)    │◄──►│  Worker     │ │
│  │  (:3000)     │    │  (:8000)         │    │  (:8080)    │ │
│  └──────┬───────┘    └────────┬─────────┘    └──────┬──────┘ │
│         │                     │                      │       │
│         ▼                     ▼                      │       │
│  ┌──────────────┐    ┌──────────────────┐            │       │
│  │  PostgreSQL  │    │  Algorand SDK    │            │       │
│  │  PostgreSQL  │    │  (py-algorand-   │            │       │
│  │  (RLS)       │    │   sdk)           │            │       │
│  └──────────────┘    └────────┬─────────┘            │       │
│                               │                       │       │
│                               ▼                       │       │
│                    ┌──────────────────┐               │       │
│                    │  TEAL Escrow     │◄──────────────┘       │
│                    │  Smart Contract  │                       │
│                    │  (Algorand App)  │                       │
│                    └──────────────────┘                       │"""

new_block = """┌──────────────────────────────────────────────────────────────┐
│                       ALGOBOUNTY PLATFORM                      │
│                                                                │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────┐ │
│  │  Next.js     │    │  FastAPI Gateway │    │ Indexer     │ │
│  │  Dashboard   │◄──►│  (REST + SSE)    │◄──►│  Worker     │ │
│  │  (:3000)     │    │  (:8000)         │    │  (:8080)    │ │
│  └──────────────┘    └────┬───────┬─────┘    └──────┬──────┘ │
│                           │       │                 │        │
│                           ▼       ▼                 │        │
│  ┌──────────────┐    ┌────────────┴─────┐           │        │
│  │  PostgreSQL  │◄───┤  Algorand SDK    │           │        │
│  │  PostgreSQL  │    │  (py-algorand-   │           │        │
│  │  (RLS)       │    │   sdk)           │           │        │
│  └──────────────┘    └────────┬─────────┘           │        │
│                               │                     │        │
│                               ▼                     │        │
│                    ┌──────────────────┐             │        │
│                    │  TEAL Escrow     │◄────────────┘        │
│                    │  Smart Contract  │                      │
│                    │  (Algorand App)  │                      │
│                    └──────────────────┘                      │"""

def modify(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # normalize newlines just in case
    content = content.replace("\r\n", "\n")

    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"Old block not found in {filepath}!")

modify("README.md")
modify("docs/index.md")
