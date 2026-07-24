'use client'

import { useFallbackContext } from '@/providers'

export function useFallbackMode() {
  const { isFallbackMode, setFallbackMode } = useFallbackContext()
  return {
    isFallbackMode,
    setFallbackMode,
  }
}
