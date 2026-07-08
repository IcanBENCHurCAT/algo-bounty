import { useState, useCallback, useEffect, useRef } from 'react';
import { useWallet as useTxnWallet } from '@txnlab/use-wallet-react';
import {
  getStoredToken,
  storeToken,
  clearToken,
  requestChallenge,
  verifyAuth,
  getMyProfile,
  type AuthChallenge,
  type AgentProfile,
} from '@/lib/api';
import algosdk from 'algosdk';
import { manager } from '@/components/AppWalletProvider';

export type WalletType = 'pera' | 'defly' | 'exodus';

export interface WalletState {
  address: string | null;
  connected: boolean;
  walletType: WalletType | null;
  jwt: string | null;
  karma: number;
  profile: AgentProfile | null;
  loading: boolean;
  error: string | null;
}

const CHALLENGE_KEY = 'algobounty_challenge';

async function getTransactionParamsResilient() {
  const nodes = [
    'https://testnet-api.algonode.cloud',
    'https://testnet-api.algorand.network'
  ];
  let lastError = null;
  for (const node of nodes) {
    try {
      const client = new algosdk.Algodv2('', node, '');
      const params = await client.getTransactionParams().do();
      return params;
    } catch (e) {
      console.warn(`Failed to fetch params from ${node}:`, e);
      lastError = e;
    }
  }
  throw lastError || new Error("Failed to fetch transaction parameters from all public nodes");
}

export function useWallet() {
  const {
    wallets,
    activeWallet,
    activeAccount,
    isReady,
    signTransactions,
    transactionSigner,
  } = useTxnWallet();

  const authInProgress = useRef(false);

  const [state, setState] = useState<WalletState>({
    address: null,
    connected: false,
    walletType: null,
    jwt: null,
    karma: 0,
    profile: null,
    loading: false,
    error: null,
  });

  const fetchProfile = useCallback(async (address: string, jwt: string) => {
    try {
      const profile = await getMyProfile(jwt);
      setState((prev) => ({ ...prev, profile, karma: profile.karma }));
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    }
  }, []);

  const connect = useCallback(async (type: WalletType = 'pera') => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      // Find the specific wallet
      const wallet = wallets.find((w) => w.id === type);
      if (!wallet) {
        throw new Error(`Wallet ${type} is not available.`);
      }

      await wallet.connect();
      wallet.setActive();
      // Connecting wraps up here. The activeAccount useEffect will handle challenge signing.
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Unknown error connecting wallet';
      setState((prev) => ({
        ...prev,
        loading: false,
        error: msg,
      }));
    }
  }, [wallets]);

  const disconnect = useCallback(() => {
    clearToken();
    const type = localStorage.getItem('algobounty_wallet_type');
    localStorage.removeItem('algobounty_wallet_type');

    if (activeWallet) {
       activeWallet.disconnect();
    }

    setState({
      address: null,
      connected: false,
      walletType: null,
      jwt: null,
      karma: 0,
      profile: null,
      loading: false,
      error: null,
    });
  }, [activeWallet]);

  const signTransaction = useCallback(async (unsignedTxnBase64: string): Promise<string> => {
    const type = localStorage.getItem('algobounty_wallet_type') || state.walletType;
    if (!state.connected || !state.address || !activeWallet) {
      return '';
    }
    if (!type) throw new Error('Wallet not connected');

    // Decode base64 to Uint8Array bytes
    const rawBytes = Uint8Array.from(atob(unsignedTxnBase64), c => c.charCodeAt(0));

    const activeWalletInstance = manager.activeWallet;
    if (!activeWalletInstance) {
      throw new Error("No active wallet in manager");
    }
    const signedTxns = await activeWalletInstance.signTransactions([rawBytes]);
    if (!signedTxns || signedTxns.length === 0) {
       throw new Error("Transaction signing failed");
    }

    return btoa(String.fromCharCode.apply(null, Array.from(signedTxns[0] || new Uint8Array())));
  }, [state.walletType, state.address, state.connected, activeWallet]);

  // Auth challenge trigger effect
  useEffect(() => {
    const jwt = getStoredToken();
    if (activeAccount && activeWallet && !jwt && !state.connected && !authInProgress.current) {
      authInProgress.current = true;
      (async () => {
        setState((prev) => ({ ...prev, loading: true, error: null }));
        try {
          const address = activeAccount.address;

          // 1. Wait for connection stability to prevent WebSocket handshake race conditions
          await new Promise((resolve) => setTimeout(resolve, 1500));

          const activeWalletInstance = manager.activeWallet;
          if (!activeWalletInstance) {
            throw new Error("No active wallet in manager");
          }

          // 2. Get challenge
          const challengeData: AuthChallenge = await requestChallenge(address);
          const challenge = challengeData.challenge;
          localStorage.setItem(CHALLENGE_KEY, challenge);

          // 3. Sign challenge (using suggested params directly to avoid 0 fee validation errors in Pera Wallet)
          const params = await getTransactionParamsResilient();
          const txn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
            sender: address,
            receiver: address,
            amount: 0,
            note: new TextEncoder().encode(`auth:${challenge}`),
            suggestedParams: params,
          });

          const encodedTxn = algosdk.encodeUnsignedTransaction(txn);
          const signedTxns = await activeWalletInstance.signTransactions([encodedTxn]);
          if (!signedTxns || signedTxns.length === 0) {
            throw new Error("Failed to sign challenge");
          }
          const signedBytes = signedTxns[0] || new Uint8Array();
          const signatureBase64 = btoa(String.fromCharCode(...signedBytes));

          // 4. Verify with backend
          const response = await verifyAuth(address, signatureBase64, challenge);

          storeToken(response.jwt);
          localStorage.setItem('algobounty_wallet_type', activeWallet?.id || '');

          setState({
            address,
            connected: true,
            walletType: (activeWallet?.id as WalletType) || null,
            jwt: response.jwt,
            karma: response.karma,
            profile: null,
            loading: false,
            error: null,
          });

          // Fetch profile in background
          fetchProfile(address, response.jwt);
        } catch (err: unknown) {
          console.error("Auth flow error:", err);
          const msg = err instanceof Error ? err.message : 'Failed to sign and authenticate wallet';
          setState((prev) => ({ ...prev, loading: false, error: msg }));
        } finally {
          authInProgress.current = false;
        }
      })();
    }
  }, [activeAccount, activeWallet, fetchProfile, state.connected]);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const jwt = getStoredToken();
    const type = localStorage.getItem('algobounty_wallet_type') as WalletType | null;

    if (jwt && activeAccount) {
      // Validate by fetching profile
      (async () => {
        setState((prev) => ({ ...prev, loading: true }));
        try {
          const profile = await getMyProfile(jwt);
          setState({
            address: profile.address,
            connected: true,
            walletType: type,
            jwt,
            karma: profile.karma,
            profile,
            loading: false,
            error: null,
          });
        } catch {
          clearToken();
          localStorage.removeItem('algobounty_wallet_type');
          if (activeWallet) activeWallet.disconnect();
          setState((prev) => ({ ...prev, jwt: null, walletType: null, connected: false, loading: false }));
        }
      })();
    } else if (!jwt) {
        if (activeWallet) activeWallet.disconnect();
    }
  }, [activeAccount, activeWallet]);

  return {
    ...state,
    connect,
    disconnect,
    signTransaction,
    setProfile: (p: AgentProfile) =>
      setState((prev) => ({ ...prev, profile: p, karma: p.karma })),
  };
}
