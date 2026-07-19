# Data Model: Dynamic Mediator Fee Safety Net & Indexer Neutrality

This document defines the schema changes and validation rules for persisting custom platform fees and treasury destinations.

---

## 1. Entity: Bounty (Updates)

The database table `bounties` is updated with two new columns to support custom fee structures per-bounty.

### Database Schema Definition

| Field Name | Type | Constraints / Nullability | Description |
|------------|------|---------------------------|-------------|
| `platform_fee` | `Integer` | `NOT NULL`, `DEFAULT 200` | Platform fee rate in basis points (e.g. 200 = 2.00%). Must be between 0 and 1000 (10.00%). |
| `treasury_address` | `String(58)` | `NOT NULL`, `DEFAULT '[Platform Treasury]'` | The Algorand address where platform fees will be sent. Must be a valid 58-character Algorand address. |

---

## 2. Validation & Business Rules

* **Platform Fee Cap**: During bounty creation (both API endpoint validation and smart contract arguments check), the system enforces:
  $$0 \le \text{platform\_fee} \le 1000$$
* **Treasury Address Format**: Validated using standard Algorand address format checks (checksum, 58 characters length).
* **Local Fallback**: For existing bounties or local SQLite fallback mode, missing fields default to `200` (for `platform_fee`) and the environment's configured platform treasury address (for `treasury_address`).
