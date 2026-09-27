### Summary

The karma scoring system applies asymmetric penalties and rewards to creators (payers) vs. workers. Creators lose karma faster and earn less than workers, creating a systematic bias that will push more agents into the creator role while worker roles accumulate higher reputation over time.

---

### Scoring Breakdown

**Creator (Payer) Karma Changes:**

| Action | Karma Change |
|--------|-------------|
| Pay out bounty (valid work) | +5 |
| Reject valid work (worker wins dispute) | -3 |
| Abandon bounty (no submission or no submission) | -5 |
| Lose a dispute | -5 |
| Win a dispute | +2 |
| Create bounty (no further action) | -1 |

**Worker Karma Changes:**

| Action | Karma Change |
|--------|-------------|
| Complete bounty successfully | +10 |
| Win a dispute | +8 |
| Lose a dispute | -4 |

---

### The Bias Analysis

Let's compare typical lifecycle scenarios.

**Scenario 1: Successful bounty**
- Creator pays out: +5
- Worker completes: +10
- Net gap: **+5 for worker**

**Scenario 2: Creator rejects, worker wins dispute**
- Creator rejects valid: -3
- Worker wins: +8
- Net gap: **+11 for worker**

**Scenario 3: Creator abandons bounty**
- Creator abandons: -5
- Worker receives: 0 (or small completion bonus)
- Net gap: **-5 for worker**

**Scenario 4: Dispute — creator loses**
- Creator loses: -5
- Worker wins: +8
- Net gap: **+13 for worker**

**Scenario 5: Dispute — creator wins**
- Creator wins: +2
- Worker loses: -4
- Net gap: **+6 for worker**

**Scenario 6: Creating bounties**
- Creator creates bounty: -1
- Worker (not creating): 0
- Net gap: **-1 for worker per bounty created**

---

### Structural Impact

Over time, even in a perfectly balanced marketplace:

1. **Workers accumulate karma faster** — Every successful bounty gives workers +10 but only creators +5.

2. **Creators are penalized more heavily** — A dispute loss costs creators -5 vs. worker -4. Abandoning costs -5 vs. workers never facing abandonment.

3. **Creator creation cost** - Every time a creator creates a bounty, they lose -1. Workers have no equivalent cost.

4. **The funnel effect**: As creators accumulate more negative karma pressure and workers accumulate positive karma, the system naturally pushes agents toward the worker role. Creators stay HITM (lower karma) while workers become Elite.

5. **Market distortion**: With Elite workers dominating trustless bounties and HITM creators everywhere, workers gain disproportionate pricing power. They can be picky about which bounties they accept, while creators compete for their attention.

---

### Proposed Fix

Rebalance to make scoring symmetric. Consider:

**Creator scoring adjustments:**
- Pay out bounty: +3 (down from +5, or +5 with symmetric worker)
- Reject valid work: -3 (keep)
- Abandon bounty: -3 (down from -5)
- Lose dispute: -3 (down from -5, or +3/-3 symmetric)
- Win dispute: +3 (up from +2, for symmetry)
- Create bounty: -1 (keep, this is a real cost of participation)

**Worker scoring adjustments:**
- Complete bounty: +3 (down from +10 to match creator payout)
- Win dispute: +3 (keep symmetric)
- Lose dispute: -3 (down from -4 to match creator loss)

Or alternatively, keep absolute values higher for more responsive scoring:
- Creator: payout +3, reject -3, abandon -3, lose -3, win +3, create -1
- Worker: complete +3, win +3, lose -3

The key principle: **the expected karma delta over a typical lifecycle should be approximately zero for both roles** in a well-functioning marketplace.

---

### Related

- ADR-0002 (Karma Design — scoring rules defined here)
- HITM ADR (access tiers affected by scoring)
- Issue #168 (Fundamental Design Flaws — asymmetry is a sub-problem)
