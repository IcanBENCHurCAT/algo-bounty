import { useState, useCallback, useEffect } from 'react';
import { useWallet as useTxnWallet } from '@txnlab/use-wallet-react';
import algosdk from 'algosdk';
import { requestChallenge, verifyAuth, getMyProfile } from '../lib/api';
import { AuthChallenge, AgentProfile } from '../types';

export type WalletType = 'pera' | 'defly' | 'exodus' | 'lute' | 'walletconnect';

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

const TOKEN_KEY = 'algobounty_jwt';
const CHALLENGE_KEY = 'algobounty_auth_challenge';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(CHALLENGE_KEY);
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

  const [authPending, setAuthPending] = useState(false);

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
      const wallet = wallets.find((w) => w.id === type);
      if (!wallet) throw new Error(`Wallet ${type} is not available.`);

      await wallet.connect();
      wallet.setActive();
      localStorage.setItem('algobounty_wallet_type', type);
      
      // Mark auth as pending so the useEffect can pick it up once activeAccount updates
      setAuthPending(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error connecting wallet';
      setState((prev) => ({ ...prev, loading: false, error: msg }));
    }
  }, [wallets]);

  const disconnect = useCallback(() => {
    clearToken();
    localStorage.removeItem('algobounty_wallet_type');
    if (activeWallet) activeWallet.disconnect();
    setAuthPending(false);
    setState({
      address: null, connected: false, walletType: null, jwt: null,
      karma: 0, profile: null, loading: false, error: null,
    });
  }, [activeWallet]);

  const signTransaction = useCallback(async (unsignedTxnBase64: string): Promise<string> => {
    const type = localStorage.getItem('algobounty_wallet_type') || state.walletType;
    if (!state.connected || !state.address || !activeWallet) return '';
    if (!type) throw new Error('Wallet not connected');

    const rawBytes = Uint8Array.from(atob(unsignedTxnBase64), c => c.charCodeAt(0));
    const signedTxns = await signTransactions([rawBytes]);
    if (!signedTxns || signedTxns.length === 0) throw new Error("Transaction signing failed");

    return btoa(String.fromCharCode.apply(null, Array.from(signedTxns[0] || new Uint8Array())));
  }, [state.walletType, state.address, state.connected, activeWallet, signTransactions]);

  // Effect to handle challenge signing automatically when wallet becomes active
  useEffect(() => {
    const jwt = getStoredToken();
    const type = localStorage.getItem('algobounty_wallet_type') as WalletType | null;

    if (authPending && activeAccount && !jwt) {
      (async () => {
        try {
          const address = activeAccount.address;
          const challengeData: AuthChallenge = await requestChallenge(address);
          const challenge = challengeData.challenge;
          localStorage.setItem(CHALLENGE_KEY, challenge);

          const algodClient = new algosdk.Algodv2('', 'https://testnet-api.algonode.cloud', ''); 
          const params = await algodClient.getTransactionParams().do();
          const txn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
            sender: address, receiver: address, amount: 0,
            note: new TextEncoder().encode(`auth:${challenge}`),
            suggestedParams: { ...params, fee: 0, flatFee: true },
          });

          const encodedTxn = algosdk.encodeUnsignedTransaction(txn);
          const signedTxns = await signTransactions([encodedTxn]);
          
          if (!signedTxns || signedTxns.length === 0) throw new Error("Failed to sign challenge");
          const signatureBase64 = Buffer.from(signedTxns[0]).toString('base64');
          
          const response = await verifyAuth(address, signatureBase64, challenge);
          storeToken(response.jwt);
          
          setState({
            address, connected: true, walletType: type, jwt: response.jwt,
            karma: response.karma, profile: null, loading: false, error: null,
          });
          
          fetchProfile(address, response.jwt);
        } catch (err: unknown) {
          console.error("Auth flow error:", err);
          const msg = err instanceof Error ? err.message : 'Authentication failed';
          setState((prev) => ({ ...prev, loading: false, error: msg }));
          if (activeWallet) activeWallet.disconnect();
        } finally {
          setAuthPending(false);
        }
      })();
    }
  }, [authPending, activeAccount, activeWallet, signTransactions, fetchProfile]);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const jwt = getStoredToken();
    const type = localStorage.getItem('algobounty_wallet_type') as WalletType | null;

    if (jwt && activeAccount) {
      (async () => {
        setState((prev) => ({ ...prev, loading: true }));
        try {
          const profile = await getMyProfile(jwt);
          setState({
            address: profile.address, connected: true, walletType: type, jwt,
            karma: profile.karma, profile, loading: false, error: null,
          });
        } catch {
          disconnect();
        }
      })();
    } else if (!jwt && !authPending) {
        if (activeWallet) activeWallet.disconnect();
    }
  }, [activeAccount, activeWallet, authPending, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    signTransaction,
    setProfile: (p: AgentProfile) =>
      setState((prev) => ({ ...prev, profile: p, karma: p.karma })),
  };
}
