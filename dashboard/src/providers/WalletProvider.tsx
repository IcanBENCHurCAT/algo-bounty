'use client'

import React from 'react'
import {
  WalletProvider as UseWalletProvider,
  WalletManager,
  NetworkId,
  WalletId,
} from '@txnlab/use-wallet-react'
import algosdk from 'algosdk'

// ─── Algod configs ────────────────────────────────────────────────────────────

type AlgodConfig = { token: string; server: string; port: number }

const ALGOD_CONFIGS: Partial<Record<NetworkId, AlgodConfig>> = {
  [NetworkId.TESTNET]: {
    token: '',
    server: 'https://testnet-api.algonode.cloud',
    port: 443,
  },
  [NetworkId.MAINNET]: {
    token: '',
    server: 'https://mainnet-api.algonode.cloud',
    port: 443,
  },
  [NetworkId.LOCALNET]: {
    token: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    server: 'http://localhost',
    port: 4001,
  },
  [NetworkId.BETANET]: {
    token: '',
    server: 'https://betanet-api.algonode.cloud',
    port: 443,
  },
}

function makeNetworkConfig(id: NetworkId) {
  const cfg = ALGOD_CONFIGS[id]
  if (!cfg) throw new Error(`No algod config for network: ${id}`)
  // use-wallet-react v4 NetworkConfig requires `algod` (the Algodv2 instance)
  return {
    algod: new algosdk.Algodv2(cfg.token, cfg.server, cfg.port),
  }
}

const defaultNetwork: NetworkId =
  (process.env.NEXT_PUBLIC_ALGORAND_NETWORK as NetworkId | undefined) ??
  NetworkId.TESTNET

// Stable singleton — created once at module level to prevent re-init on renders
const manager = new WalletManager({
  wallets: [WalletId.PERA, WalletId.DEFLY, WalletId.EXODUS],
  networks: {
    [NetworkId.TESTNET]: makeNetworkConfig(NetworkId.TESTNET),
    [NetworkId.MAINNET]: makeNetworkConfig(NetworkId.MAINNET),
    [NetworkId.LOCALNET]: makeNetworkConfig(NetworkId.LOCALNET),
  },
  defaultNetwork,
})

// ─── Provider ─────────────────────────────────────────────────────────────────

export function WalletProvider({ children }: { children: React.ReactNode }) {
  return (
    <UseWalletProvider manager={manager}>
      {children}
    </UseWalletProvider>
  )
}
