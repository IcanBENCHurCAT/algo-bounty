import { useState, useCallback, useEffect } from 'react';
import { PeraWalletConnect } from '@perawallet/connect';
import algosdk from 'algosdk';
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

export type WalletType = 'pera' | 'defly' | 'edge';

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


interface WalletWindow extends Window {
  algoransdk?: {
    signTxn: (txn: string, sk: string) => Promise<string>;
  };
  DeflyWalletConnect?: new () => { connect: () => Promise<void>; account: string | null; signMessage: (data: { message: string }) => Promise<Uint8Array | Uint8Array[]>; signTransaction: (txns: unknown[]) => Promise<Uint8Array[]>; disconnect?: () => void };
  EdgeWalletConnect?: new () => { connect: () => Promise<void>; account: string | null; signMessage: (data: { message: string }) => Promise<Uint8Array | Uint8Array[]>; signTransaction: (txns: unknown[]) => Promise<Uint8Array[]>; disconnect?: () => void };
}

declare const window: WalletWindow;

const CHALLENGE_KEY = 'algobounty_challenge';


const peraWallet = typeof window !== 'undefined' ? new PeraWalletConnect() : null;

export function useWallet() {
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
      let wallet: { connect: () => Promise<void>; account: string | null; signMessage: (data: { message: string }) => Promise<Uint8Array | Uint8Array[]> } | null = null;
      let address: string | null = null;

      if (type === 'pera') {
        if (!peraWallet) throw new Error('Pera Wallet is not initialized');
        const accounts = await peraWallet.connect();
        address = accounts[0];
      } else if (type === 'defly') {
        const Defly = window.DeflyWalletConnect;
        if (!Defly) throw new Error('Defly Wallet is not installed');
        wallet = new Defly();
        await wallet.connect();
        address = wallet.account;
      } else {
        const Edge = window.EdgeWalletConnect;
        if (!Edge) throw new Error('Edge Wallet is not installed');
        wallet = new Edge();
        await wallet.connect();
        address = wallet.account;
      }

      if (!address) throw new Error(`No account returned from ${type} wallet`);

      // Get challenge
      const challengeData: AuthChallenge = await requestChallenge();
      const challenge = challengeData.challenge;
      localStorage.setItem(CHALLENGE_KEY, challenge);

      // Sign challenge
      let signature: string;
      try {
        let signed;
        if (type === 'pera' && peraWallet) {
           const dataToSign = [{ data: Uint8Array.from(challenge, c => c.charCodeAt(0)), signer: address, message: challenge }];
           signed = await peraWallet.signData(dataToSign, address);
        } else {
           if (!wallet) throw new Error('Wallet not initialized');
           signed = await wallet.signMessage({ message: challenge });
        }
        signature = Array.isArray(signed)
          ? Buffer.from(signed[0]).toString('base64')
          : Buffer.from(signed as Uint8Array).toString('base64');
      } catch (signErr) {
        console.error(`${type} sign error:`, signErr);
        throw new Error(`Failed to sign challenge with ${type} Wallet`);
      }

      // Verify with backend
      const response = await verifyAuth(address, signature, challenge);

      storeToken(response.jwt);
      localStorage.setItem('algobounty_wallet_type', type);

      setState({
        address,
        connected: true,
        walletType: type,
        jwt: response.jwt,
        karma: response.karma,
        profile: null,
        loading: false,
        error: null,
      });

      // Fetch profile in background
      fetchProfile(address, response.jwt);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Unknown error connecting wallet';
      setState((prev) => ({
        ...prev,
        loading: false,
        error: msg,
      }));
    }
  }, [fetchProfile]);

  const disconnect = useCallback(() => {
    clearToken();
    const type = localStorage.getItem('algobounty_wallet_type');
    localStorage.removeItem('algobounty_wallet_type');

    try {
      if (type === 'pera' && peraWallet) {
        peraWallet.disconnect?.();
      } else if (type === 'defly' && window.DeflyWalletConnect) {
        new window.DeflyWalletConnect().disconnect?.();
      } else if (type === 'edge' && window.EdgeWalletConnect) {
        new window.EdgeWalletConnect().disconnect?.();
      }
    } catch {
      // Ignore disconnect errors
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
  }, []);

  const signTransaction = useCallback(async (unsignedTxnBase64: string): Promise<string> => {
    const type = localStorage.getItem('algobounty_wallet_type') || state.walletType;
    if (!state.connected || !state.address) {
      return '';
    }
    if (!type) throw new Error('Wallet not connected');

    // Decode base64 to Uint8Array bytes
    const rawBytes = Uint8Array.from(atob(unsignedTxnBase64), c => c.charCodeAt(0));

    let signedBase64 = '';
    if (type === 'pera') {
      if (!peraWallet) throw new Error('Pera Wallet is not initialized');
      const txn = algosdk.decodeUnsignedTransaction(rawBytes);
      const txnsToSign = [{ txn, signers: [state.address] }];
      const signedTxns = await peraWallet.signTransaction([txnsToSign]);
      signedBase64 = btoa(String.fromCharCode.apply(null, Array.from(signedTxns[0])));
    } else if (type === 'defly') {
      const Defly = window.DeflyWalletConnect;
      if (!Defly) throw new Error('Defly Wallet is not installed');
      const wallet = new Defly();
      await wallet.connect();
      const txn = algosdk.decodeUnsignedTransaction(rawBytes);
      const txnsToSign = [{ txn, signers: [state.address] }];
      const signedTxns = await wallet.signTransaction([txnsToSign]);
      signedBase64 = btoa(String.fromCharCode.apply(null, Array.from(signedTxns[0])));
    } else {
      const Edge = window.EdgeWalletConnect;
      if (!Edge) throw new Error('Edge Wallet is not installed');
      const wallet = new Edge();
      await wallet.connect();
      const txn = algosdk.decodeUnsignedTransaction(rawBytes);
      const txnsToSign = [{ txn, signers: [state.address] }];
      const signedTxns = await wallet.signTransaction([txnsToSign]);
      signedBase64 = btoa(String.fromCharCode.apply(null, Array.from(signedTxns[0])));
    }
    return signedBase64;
  }, [state.walletType, state.address, state.connected]);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const jwt = getStoredToken();
    const type = localStorage.getItem('algobounty_wallet_type') as WalletType | null;

    if (jwt) {
      // Validate by fetching profile
      (async () => {
        setState((prev) => ({ ...prev, loading: true }));
        try {
          if (type === 'pera' && peraWallet) {
            await peraWallet.reconnectSession();
          }
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
          setState((prev) => ({ ...prev, jwt: null, walletType: null, connected: false, loading: false }));
        }
      })();
    }
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    signTransaction,
    setProfile: (p: AgentProfile) =>
      setState((prev) => ({ ...prev, profile: p, karma: p.karma })),
  };
}
