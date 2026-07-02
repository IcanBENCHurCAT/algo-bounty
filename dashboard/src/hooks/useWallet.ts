import { useState, useCallback, useEffect, useRef } from 'react';
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

export interface WalletState {
  address: string | null;
  connected: boolean;
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
  PeraWalletConnect?: any;
}

declare const window: WalletWindow;

const CHALLENGE_KEY = 'algobounty_challenge';

export function useWallet() {
  const [state, setState] = useState<WalletState>({
    address: null,
    connected: false,
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

  const connect = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      // Detect Pera Wallet
      const Pera = window.PeraWalletConnect;
      if (!Pera) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            'Pera Wallet is not installed. Please install Pera Wallet to connect.',
        }));
        return;
      }

      const pera = new Pera();

      // Request connection
      await pera.connect();
      const address = pera.account;
      if (!address) throw new Error('No account returned from Pera');

      // Get challenge
      const challengeData: AuthChallenge = await requestChallenge();
      const challenge = challengeData.challenge;
      localStorage.setItem(CHALLENGE_KEY, challenge);

      // Sign challenge with Pera
      let signature: string;
      try {
        const signed = await pera.signMessage({ message: challenge });
        signature = Array.isArray(signed)
          ? Buffer.from(signed[0]).toString('base64')
          : Buffer.from(signed as Uint8Array).toString('base64');
      } catch (signErr) {
        console.error('Pera sign error:', signErr);
        throw new Error('Failed to sign challenge with Pera Wallet');
      }

      // Verify with backend
      const response = await verifyAuth(address, signature, challenge);

      storeToken(response.jwt);
      setState({
        address,
        connected: true,
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
    try {
      if (window.PeraWalletConnect) {
        const pera = new (window.PeraWalletConnect as any)();
        pera.disconnect?.();
      }
    } catch {
      // Ignore disconnect errors
    }
    setState({
      address: null,
      connected: false,
      jwt: null,
      karma: 0,
      profile: null,
      loading: false,
      error: null,
    });
  }, []);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const jwt = getStoredToken();
    if (jwt) {
      // Validate by fetching profile
      (async () => {
        setState((prev) => ({ ...prev, loading: true }));
        try {
          const profile = await getMyProfile(jwt);
          setState({
            address: profile.address,
            connected: true,
            jwt,
            karma: profile.karma,
            profile,
            loading: false,
            error: null,
          });
        } catch {
          clearToken();
          setState((prev) => ({ ...prev, jwt: null, connected: false, loading: false }));
        }
      })();
    }
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    setProfile: (p: AgentProfile) =>
      setState((prev) => ({ ...prev, profile: p, karma: p.karma })),
  };
}
