'use client'

import React from 'react'
import {
  WalletProvider as UseWalletProvider,
  WalletManager,
  NetworkId,
  WalletId,
} from '@txnlab/use-wallet-react'

// ─── Network configs ──────────────────────────────────────────────────────────
// NetworkConfig.algod expects AlgodConfig { token, baseServer, port? }
// NOT an instantiated Algodv2 client.

const NETWORKS: Partial<Record<NetworkId, { algod: { token: string; baseServer: string; port?: number } }>> = {
  [NetworkId.TESTNET]: {
    algod: {
      token: '',
      baseServer: 'https://testnet-api.algonode.cloud',
      port: 443,
    },
  },
  [NetworkId.MAINNET]: {
    algod: {
      token: '',
      baseServer: 'https://mainnet-api.algonode.cloud',
      port: 443,
    },
  },
  [NetworkId.LOCALNET]: {
    algod: {
      token: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      baseServer: 'http://localhost',
      port: 4001,
    },
  },
}

const defaultNetwork: NetworkId =
  (process.env.NEXT_PUBLIC_ALGORAND_NETWORK as NetworkId | undefined) ??
  NetworkId.TESTNET

// Stable singleton — created once at module level to prevent re-init on renders
const manager = new WalletManager({
  wallets: [WalletId.PERA, WalletId.DEFLY, WalletId.EXODUS],
  networks: NETWORKS,
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
