'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Bounty, BountyFilters } from '@/types'
import { getBounties } from '@/lib/api'
import { useFallbackMode } from '@/hooks/useFallbackMode'
import { fetchBountiesFromChain } from '@/services/indexerFallback'

interface UseBountiesReturn {
  bounties: Bounty[]
  loading: boolean
  error: string | null
  page: number
  hasMore: boolean
  total: number
  loadMore: () => void
  refresh: () => void
}

const DEFAULT_LIMIT = 20

export function useBounties(filters: BountyFilters = {}): UseBountiesReturn {
  const [bounties, setBounties] = useState<Bounty[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)
  
  const { isFallbackMode, setFallbackMode } = useFallbackMode()

  // Stable ref for filters to avoid stale closures
  const filtersRef = useRef(filters)
  filtersRef.current = filters

  const load = useCallback(async (targetPage: number, append = false) => {
    setLoading(true)
    setError(null)
    
    if (isFallbackMode) {
      try {
        const chainBounties = await fetchBountiesFromChain()
        setBounties(chainBounties)
        setHasMore(false)
        setTotal(chainBounties.length)
        setPage(1)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load bounties from chain')
      } finally {
        setLoading(false)
      }
      return
    }

    try {
      const resp = await getBounties({
        ...filtersRef.current,
        page: targetPage,
        limit: DEFAULT_LIMIT,
      })
      setBounties((prev) => (append ? [...prev, ...resp.bounties] : resp.bounties))
      setHasMore(resp.has_more)
      setTotal(resp.total)
      setPage(targetPage)
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : ''
      const isNetworkOr5xx = 
        errMsg.includes('Failed to fetch') ||
        errMsg.includes('NetworkError') ||
        errMsg.includes('HTTP 5') ||
        errMsg.includes('500') ||
        errMsg.includes('502') ||
        errMsg.includes('503') ||
        errMsg.includes('504')

      if (isNetworkOr5xx) {
        setFallbackMode(true)
        try {
          const chainBounties = await fetchBountiesFromChain()
          setBounties(chainBounties)
          setHasMore(false)
          setTotal(chainBounties.length)
          setPage(1)
        } catch (chainErr) {
          setError('Gateway offline. Failed to fetch fallback data from Algorand: ' + (chainErr instanceof Error ? chainErr.message : 'unknown error'))
        }
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to load bounties'
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [isFallbackMode, setFallbackMode])

  // Initial load and re-load when filters change
  useEffect(() => {
    setBounties([])
    setPage(1)
    void load(1, false)
  // Stringify filters so the effect compares by value, not reference
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters), load])

  const loadMore = useCallback(() => {
    if (!hasMore || loading) return
    void load(page + 1, true)
  }, [hasMore, loading, page, load])

  const refresh = useCallback(() => {
    void load(1, false)
  }, [load])

  return { bounties, loading, error, page, hasMore, total, loadMore, refresh }
}
