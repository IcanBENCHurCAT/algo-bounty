'use client';

import { ReactNode } from 'react';
import { WalletProvider, WalletManager, NetworkId, WalletId } from '@txnlab/use-wallet-react';

export const manager = new WalletManager({
  wallets: [WalletId.PERA, WalletId.DEFLY, WalletId.EXODUS], // Adding Exodus as an example, but adjust based on previous needs, originally 'edge' was listed but maybe it is 'exodus' that's standard.
  defaultNetwork: NetworkId.TESTNET
});

export default function AppWalletProvider({ children }: { children: ReactNode }) {
  return <WalletProvider manager={manager}>{children}</WalletProvider>;
}
