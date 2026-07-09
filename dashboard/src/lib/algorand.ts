/**
 * algorand.ts — AlgoKit-aligned Algorand utilities
 *
 * Uses @algorandfoundation/algokit-utils for high-level operations
 * and algosdk for low-level transaction construction.
 */
import algosdk from 'algosdk'

// ─── Network config ───────────────────────────────────────────────────────────

const NETWORKS = {
  testnet: {
    algodToken: '',
    algodServer: 'https://testnet-api.algonode.cloud',
    algodPort: 443,
    indexerServer: 'https://testnet-idx.algonode.cloud',
    indexerPort: 443,
  },
  mainnet: {
    algodToken: '',
    algodServer: 'https://mainnet-api.algonode.cloud',
    algodPort: 443,
    indexerServer: 'https://mainnet-idx.algonode.cloud',
    indexerPort: 443,
  },
  localnet: {
    algodToken: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    algodServer: 'http://localhost',
    algodPort: 4001,
    indexerServer: 'http://localhost',
    indexerPort: 8980,
  },
} as const

export type NetworkName = keyof typeof NETWORKS

export function getNetworkName(): NetworkName {
  const env = process.env.NEXT_PUBLIC_ALGORAND_NETWORK ?? 'testnet'
  if (env in NETWORKS) return env as NetworkName
  return 'testnet'
}

// ─── Algod client factory ─────────────────────────────────────────────────────

export function getAlgodClient(network?: NetworkName): algosdk.Algodv2 {
  const cfg = NETWORKS[network ?? getNetworkName()]
  return new algosdk.Algodv2(cfg.algodToken, cfg.algodServer, cfg.algodPort)
}

// ─── Auth transaction builder ─────────────────────────────────────────────────

/**
 * Builds a zero-amount payment transaction containing the auth challenge in
 * its note field. This is signed by the user's wallet to prove ownership.
 *
 * Pattern: sign txn note `auth:{challenge}` → extract signature → verify server-side.
 */
export async function buildAuthTransaction(
  address: string,
  challenge: string,
  algodClient: algosdk.Algodv2,
): Promise<algosdk.Transaction> {
  const suggestedParams = await algodClient.getTransactionParams().do()

  const note = new TextEncoder().encode(`auth:${challenge}`)

  return algosdk.makePaymentTxnWithSuggestedParamsFromObject({
    sender: address,
    receiver: address,
    amount: 0,
    note,
    suggestedParams,
  })
}

/**
 * Encodes a transaction to base64 Uint8Array for transport to wallet signers.
 */
export function encodeTransactionForSigning(txn: algosdk.Transaction): Uint8Array {
  return txn.toByte()
}

/**
 * Extracts the Ed25519 signature bytes from a signed transaction and
 * returns them as a base64 string for the auth/verify endpoint.
 */
export function extractSignatureBase64(signedTxnBytes: Uint8Array): string {
  const decoded = algosdk.decodeSignedTransaction(signedTxnBytes)
  // The signature is in decoded.sig — it's already a Uint8Array
  const sig = decoded.sig
  if (!sig) throw new Error('No signature found in signed transaction')
  return Buffer.from(sig).toString('base64')
}

/**
 * Converts a base64-encoded transaction to Uint8Array.
 */
export function base64ToBytes(b64: string): Uint8Array {
  return Uint8Array.from(Buffer.from(b64, 'base64'))
}

/**
 * Converts raw bytes to base64 string.
 */
export function bytesToBase64(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString('base64')
}

/**
 * Converts microALGO amount to ALGO display string.
 */
export function microAlgoToAlgo(microAlgo: number): string {
  return (microAlgo / 1_000_000).toFixed(6).replace(/\.?0+$/, '')
}

/**
 * Converts ALGO to microALGO.
 */
export function algoToMicroAlgo(algo: number): number {
  return Math.round(algo * 1_000_000)
}
