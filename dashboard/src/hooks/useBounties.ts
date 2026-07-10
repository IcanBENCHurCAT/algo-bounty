'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Bounty, BountyFilters } from '@/types'
import { getBounties } from '@/lib/api'

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

/**
 * useBounties — manages bounty list fetching with pagination.
 *
 * BUG FIX: The original page.tsx used `useState(() => loadBounties(1))` as the
 * initial state setter — this is broken because useState initializer returns
 * the initial state value synchronously (undefined here), not await the promise.
 * Fixed: proper useEffect with deps array.
 */
export function useBounties(filters: BountyFilters = {}): UseBountiesReturn {
  const [bounties, setBounties] = useState<Bounty[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)

  // Stable ref for filters to avoid stale closures
  const filtersRef = useRef(filters)
  filtersRef.current = filters

  const load = useCallback(async (targetPage: number, append = false) => {
    setLoading(true)
    setError(null)
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
      const msg = err instanceof Error ? err.message : 'Failed to load bounties'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

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
