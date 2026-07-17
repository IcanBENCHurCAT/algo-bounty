---
name: "algo-wallet-auth"
description: "Guidelines for implementing Algorand wallet authentication and transaction signing in the dashboard frontend."
compatibility: "Next.js dashboard using @txnlab/use-wallet-react."
metadata:
  author: "algobounty-project"
  source: "custom-skills"
---

## Description
The frontend `dashboard` application uses `@txnlab/use-wallet-react` (v4.x) for wallet integration. Authentication is managed centrally via a client-side `src/providers/WalletProvider.tsx` component and `src/providers/AuthProvider.tsx`.

## Key Practices

### 1. Handling Authentication Challenges
When building authentication flows (e.g., in `AuthProvider.tsx`), check if the wallet natively supports data signing:
```typescript
if (activeWallet?.canSignData) {
  // Use native data signing if supported
} else {
  // Fallback for wallets that don't support signData natively (like Defly or Pera on some platforms).
  // Use a zero-amount, zero-fee, self-payment transaction containing the challenge in the `note` field.
}
```
**Backend Expectation:** The backend expects the *entire Msgpack-encoded signed transaction as a base64 string*, not just the extracted signature bytes, for the fallback method.

### 2. Algod Client Usage
For Algorand transaction parameters, strictly use the `algodClient` provided by the `@txnlab/use-wallet-react` hook context rather than querying hardcoded public nodes. This prevents CORS and rate-limiting issues.
```typescript
import { useWallet } from '@txnlab/use-wallet-react';

const { algodClient } = useWallet();
const params = await algodClient.getTransactionParams().do();
```

### 3. Preventing Infinite Loops
To prevent infinite wallet signature request loops on page refresh, the dashboard authentication flow must trigger the signature challenge manually upon a user's explicit `connect()` action, rather than via an automatic `useEffect` detecting an active wallet.

### 4. Optional Chaining
Wallet `address` variables can be undefined during hydration or before connection. Always use optional chaining (`?.`) or safe fallbacks when referencing them.
