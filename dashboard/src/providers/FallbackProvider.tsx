'use client'

import React, { createContext, useContext, useState } from 'react'

interface FallbackContextType {
  isFallbackMode: boolean
  setFallbackMode: (active: boolean) => void
}

const FallbackContext = createContext<FallbackContextType | undefined>(undefined)

export function FallbackProvider({ children }: { children: React.ReactNode }) {
  const [isFallbackMode, setIsFallbackMode] = useState(false)

  return (
    <FallbackContext.Provider value={{ isFallbackMode, setFallbackMode: setIsFallbackMode }}>
      {children}
    </FallbackContext.Provider>
  )
}

export function useFallbackContext() {
  const context = useContext(FallbackContext)
  if (context === undefined) {
    throw new Error('useFallbackContext must be used within a FallbackProvider')
  }
  return context
}
