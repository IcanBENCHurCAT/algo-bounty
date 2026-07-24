'use client'

import React from 'react'
import { WalletProvider } from './WalletProvider'
import { AuthProvider } from './AuthProvider'
import { ToastProvider } from './ToastProvider'
import { FallbackProvider, useFallbackContext } from './FallbackProvider'

export { useAuthContext } from './AuthProvider'
export { useToast } from './ToastProvider'
export { useFallbackContext }

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <WalletProvider>
      <FallbackProvider>
        <AuthProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </AuthProvider>
      </FallbackProvider>
    </WalletProvider>
  )
}
