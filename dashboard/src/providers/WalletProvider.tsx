'use client'

import React, { useMemo } from 'react'
import { WalletProvider as UseWalletProvider, WalletManager, NetworkId, WalletId } from '@txnlab/use-wallet-react'
import algosdk from 'algosdk'

// Custom algod configuration pointing to Algonode public endpoints
const ALGOD_CONFIG: Record<NetworkId, { token: string; server: string; port: number }> = {
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
  [NetworkId.FNET]: {
    token: '',
    server: 'https://fnet-api.algonode.cloud',
    port: 443,
  },
  [NetworkId.VOIMAIN]: {
    token: '',
    server: 'https://mainnet-api.voi.nodely.dev',
    port: 443,
  },
}

function makeNetworkConfig(id: NetworkId) {
  const cfg = ALGOD_CONFIG[id]
  return {
    algodClient: new algosdk.Algodv2(cfg.token, cfg.server, cfg.port),
  }
}

const defaultNetwork: NetworkId =
  (process.env.NEXT_PUBLIC_ALGORAND_NETWORK as NetworkId) ?? NetworkId.TESTNET

// Stable WalletManager singleton — created once outside the component
// to prevent re-initialization on re-renders.
const manager = new WalletManager({
  wallets: [
    WalletId.PERA,
    WalletId.DEFLY,
    WalletId.EXODUS,
  ],
  networks: {
    [NetworkId.TESTNET]: makeNetworkConfig(NetworkId.TESTNET),
    [NetworkId.MAINNET]: makeNetworkConfig(NetworkId.MAINNET),
    [NetworkId.LOCALNET]: makeNetworkConfig(NetworkId.LOCALNET),
  },
  defaultNetwork,
})

interface WalletProviderProps {
  children: React.ReactNode
}

export function WalletProvider({ children }: WalletProviderProps) {
  return (
    <UseWalletProvider manager={manager}>
      {children}
    </UseWalletProvider>
  )
}
