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

async function fetchBountiesPage(
  currentFilters: BountyFilters,
  targetPage: number,
  isFallbackMode: boolean,
  setFallbackMode: (value: boolean) => void,
): Promise<{ bounties: Bounty[]; hasMore: boolean; total: number; page: number }> {
  if (isFallbackMode) {
    const chainBounties = await fetchBountiesFromChain()
    return {
      bounties: chainBounties,
      hasMore: false,
      total: chainBounties.length,
      page: 1,
    }
  }

  try {
    const resp = await getBounties({
      ...currentFilters,
      page: targetPage,
      limit: DEFAULT_LIMIT,
    })
    return {
      bounties: resp.bounties,
      hasMore: resp.has_more,
      total: resp.total,
      page: targetPage,
    }
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
        return {
          bounties: chainBounties,
          hasMore: false,
          total: chainBounties.length,
          page: 1,
        }
      } catch (chainErr) {
        throw new Error(
          'Gateway offline. Failed to fetch fallback data from Algorand: ' +
            (chainErr instanceof Error ? chainErr.message : 'unknown error'),
        )
      }
    }
    throw err
  }
}

export function useBounties(filters: BountyFilters = {}): UseBountiesReturn {
  const [bounties, setBounties] = useState<Bounty[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)
  const [loadedFilterKey, setLoadedFilterKey] = useState<string | null>(null)

  const { isFallbackMode, setFallbackMode } = useFallbackMode()

  // Stable ref for filters to avoid stale closures
  const filtersRef = useRef(filters)
  const filterKey = JSON.stringify(filters)

  useEffect(() => {
    filtersRef.current = filters
  })

  const load = useCallback(async (targetPage: number, append = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchBountiesPage(
        filtersRef.current,
        targetPage,
        isFallbackMode,
        setFallbackMode,
      )
      setBounties((prev) => (append ? [...prev, ...res.bounties] : res.bounties))
      setHasMore(res.hasMore)
      setTotal(res.total)
      setPage(res.page)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load bounties')
    } finally {
      setLoading(false)
    }
  }, [isFallbackMode, setFallbackMode])

  // Initial load and re-load when filters change
  useEffect(() => {
    let cancelled = false
    fetchBountiesPage(filtersRef.current, 1, isFallbackMode, setFallbackMode)
      .then((res) => {
        if (cancelled) return
        setBounties(res.bounties)
        setHasMore(res.hasMore)
        setTotal(res.total)
        setPage(res.page)
        setError(null)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load bounties')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadedFilterKey(filterKey)
      })
    return () => {
      cancelled = true
    }
  }, [filterKey, isFallbackMode, setFallbackMode])

  const loadMore = useCallback(() => {
    if (!hasMore || loading) return
    void load(page + 1, true)
  }, [hasMore, loading, page, load])

  const refresh = useCallback(() => {
    void load(1, false)
  }, [load])

  const isInitialLoading = loadedFilterKey !== filterKey
  return {
    bounties: isInitialLoading ? [] : bounties,
    loading: loading || isInitialLoading,
    error: isInitialLoading ? null : error,
    page: isInitialLoading ? 1 : page,
    hasMore: isInitialLoading ? false : hasMore,
    total: isInitialLoading ? 0 : total,
    loadMore,
    refresh,
  }
}
