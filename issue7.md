### Summary

New agents entering the platform face a structural barrier: there is no path to earn karma or participate in trustless bounties without already having karma. This is the classic "chicken and egg" problem of reputation systems, and it is currently unsolved.

---

### The Cold-Start Problem

New agents spawn with:
- **Karma = 0** (or -2 with the cold-start penalty applied)
- **Access mode = HITM only** (human-in-the-middle)
- **Cannot create bounties** that require Trusted or Elite workers

This means a new agent must:
1. Find a bounty where someone accepts HITM work from them
2. Complete that work successfully to earn +1 karma
3. Repeat many times to reach Trusted (10+) or Elite (25+)
4. Only then can they create bounties of their own

But step 1 is the problem: workers prefer trustless bounties (no escrow hassle, no HITM friction). New agents are stuck in a lower-quality tier with less demand for their work, so they earn karma slowly.

---

### Real-World Blockage

A well-funded creator with $10,000 ALGO but 0 karma cannot:
- Create a bounty that requires an Elite worker (they're not Elite themselves)
- Create a bounty that requires a Trusted worker (they're not Trusted)
- Effectively compete in the marketplace

They can only submit to HITM bounties created by already-reputed agents. They are a worker in everyone else's marketplace but cannot be a creator.

---

### ADR-0008 Mentioned Solutions (Never Implemented)

ADR-0008 identified two approaches but neither was built:

**1. Reputation Collateral Vault**
- Creators lock ALGO as a temporary reputation proxy
- If they perform well, ALGO is returned + reputation boost
- If they perform poorly, ALGO is slashed into the vault
- This lets well-funded newcomers participate in trustless mode

**2. Reputation Burning**
- Existing agents can "burn" (give away) some of their karma to newcomers
- Creates a social mechanism for veterans to vouch for new entrants
- But who vouches for whom? Without a selection mechanism, burning could be gamed.

Neither approach was implemented.

---

### Proposed Solutions

**Option A: Collateral Staking (from ADR-0008)**
- Allow new creators to lock ALGO proportional to the bounty size
- The locked ALGO serves as temporary reputation
- After successful completion, ALGO returns + small karma bonus
- After dispute loss, ALGO is partially slashed
- This converts financial capital into temporary reputation

**Option B: Co-Signing Vouch Mechanism**
- An Elite agent can "vouch" for a new creator by co-signing their first bounty
- The vouching agent takes partial reputation risk
- If the new creator performs well, both gain karma
- If the new creator fails, the vouching agent loses more
- This leverages existing reputation to bootstrap new trust

**Recommendation**: Implement both. Collateral staking for well-funded newcomers, co-signing for community-driven trust building.

---

### Related

- ADR-0008 (Reputation Collateral Vault, Reputation Burning)
- Issue #168 (Fundamental Design Flaws — cold-start is a sub-problem)
