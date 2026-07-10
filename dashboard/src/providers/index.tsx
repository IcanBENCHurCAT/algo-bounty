'use client'

import React from 'react'
import { WalletProvider } from './WalletProvider'
import { AuthProvider } from './AuthProvider'
import { ToastProvider } from './ToastProvider'

export { useAuthContext } from './AuthProvider'
export { useToast } from './ToastProvider'

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <WalletProvider>
      <AuthProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </AuthProvider>
    </WalletProvider>
  )
}
