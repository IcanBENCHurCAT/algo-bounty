'use client'
/**
 * useAuth — consumes the WalletAuthContext set up by AuthProvider.
 *
 * This is the primary hook for components to access auth state:
 * address, jwt, karma, profile, connected status, and actions.
 */
export { useAuthContext as useAuth } from '@/providers'
