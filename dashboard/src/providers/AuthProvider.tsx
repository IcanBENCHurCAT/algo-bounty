'use client'

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useWallet } from '@txnlab/use-wallet-react'
import type { WalletAuthState, AgentProfile } from '@/types'
import {
  requestChallenge,
  verifyAuth,
  getMyProfile,
  getStoredToken,
  storeToken,
  clearToken,
} from '@/lib/api'
import {
  getAlgodClient,
  buildAuthTransaction,
  encodeTransactionForSigning,
  extractSignatureBase64,
  bytesToBase64,
  base64ToBytes,
} from '@/lib/algorand'

// ─── Context types ────────────────────────────────────────────────────────────

interface AuthContextValue extends WalletAuthState {
  connect: (walletId: string) => Promise<void>
  disconnect: () => Promise<void>
  signTransaction: (unsignedTxnBase64: string) => Promise<string>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const {
    wallets,
    activeWallet,
    activeAccount,
    isReady,
    signTransactions,
  } = useWallet()

  const [state, setState] = useState<WalletAuthState>({
    address: null,
    connected: false,
    walletType: null,
    jwt: null,
    karma: 0,
    profile: null,
    loading: false,
    error: null,
  })

  const authInProgress = useRef(false)

const performAuth = useCallback(async (address: string, walletId: string) => {
    authInProgress.current = true
    setState((s) => ({ ...s, loading: true, error: null }))

    try {
      // 1. Get challenge from backend
      const { challenge } = await requestChallenge(address)

      // 2. Build auth transaction with challenge in note field
      const algodClient = getAlgodClient()
      const authTxn = await buildAuthTransaction(address, challenge, algodClient)
      const encodedTxn = encodeTransactionForSigning(authTxn)

      // 3. Ask wallet to sign
      const signedTxns = await signTransactions([encodedTxn])
      const signedBytes = signedTxns[0]
      if (!signedBytes) throw new Error('Wallet rejected signing')

      // 4. Send full signed transaction (as base64) to backend
      const signatureBase64 = bytesToBase64(signedBytes)
      const { jwt, karma } = await verifyAuth(address, signatureBase64, challenge)

      // 5. Store JWT and fetch profile
      storeToken(jwt)
      let profile: AgentProfile | null = null
      try {
        profile = await getMyProfile(jwt)
      } catch {
        // profile fetch failure is non-fatal
      }

      setState({
        address,
        connected: true,
        walletType: walletId,
        jwt,
        karma: profile?.karma ?? karma,
        profile,
        loading: false,
        error: null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Authentication failed'
      setState((s) => ({ ...s, loading: false, error: msg }))
      authInProgress.current = false
    }
  }, [signTransactions])

  // ─── Connect ───────────────────────────────────────────────────────────────

  const connect = useCallback(
    async (walletId: string) => {
      setState((s) => ({ ...s, loading: true, error: null }))
      try {
        const wallet = wallets.find((w) => w.id === walletId)
        if (!wallet) throw new Error(`Wallet ${walletId} not available`)
        await wallet.connect()
        await wallet.setActive()

        // After connecting, wallet.activeAccount might not be immediately available
        // Wait for it, or get it from the wallet object

        // The wallet object has an activeAccount property once connected
        const accounts = wallet.accounts
        if (!accounts || accounts.length === 0) {
           throw new Error("No accounts found in wallet")
        }
        const activeAddress = accounts[0].address

        await performAuth(activeAddress, walletId)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Connection failed'
        setState((s) => ({ ...s, loading: false, error: msg }))
      }
    },
    [wallets, performAuth],
  )

  // ─── Disconnect ────────────────────────────────────────────────────────────

  const disconnect = useCallback(async () => {
    clearToken()
    authInProgress.current = false
    setState({
      address: null,
      connected: false,
      walletType: null,
      jwt: null,
      karma: 0,
      profile: null,
      loading: false,
      error: null,
    })
    try {
      await activeWallet?.disconnect()
    } catch {
      // ignore disconnect errors
    }
  }, [activeWallet])

  // ─── Sign transaction ──────────────────────────────────────────────────────

  const signTransaction = useCallback(
    async (unsignedTxnBase64: string): Promise<string> => {
      const rawBytes = base64ToBytes(unsignedTxnBase64)
      const signed = await signTransactions([rawBytes])
      const signedBytes = signed[0]
      if (!signedBytes) throw new Error('Wallet rejected signing')
      return bytesToBase64(signedBytes)
    },
    [signTransactions],
  )

  // ─── Refresh profile ───────────────────────────────────────────────────────

  const refreshProfile = useCallback(async () => {
    const token = state.jwt ?? getStoredToken()
    if (!token) return
    try {
      const profile = await getMyProfile(token)
      setState((s) => ({ ...s, profile, karma: profile.karma }))
    } catch {
      // silently fail
    }
  }, [state.jwt])

    // ─── Session hydration: restore JWT on mount ───────────────────────────────

  useEffect(() => {
    if (!isReady || !activeAccount) return
    const storedJwt = getStoredToken()
    if (!storedJwt || state.jwt) return

    // Validate stored JWT by fetching profile
    getMyProfile(storedJwt)
      .then((profile) => {
        setState({
          address: activeAccount.address,
          connected: true,
          walletType: activeWallet?.id ?? null,
          jwt: storedJwt,
          karma: profile.karma,
          profile,
          loading: false,
          error: null,
        })
        authInProgress.current = true // mark as already authed
      })
      .catch(() => {
        // JWT expired or invalid — clear and let auth flow re-run
        clearToken()
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady, activeAccount])

  const value: AuthContextValue = {
    ...state,
    connect,
    disconnect,
    signTransaction,
    refreshProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuthContext must be used inside <AuthProvider>')
  }
  return ctx
}
