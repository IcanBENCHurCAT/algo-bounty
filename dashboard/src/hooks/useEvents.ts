'use client'

import { useCallback, useEffect, useRef } from 'react'
import type { SseEvent, SseEventType } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

const SSE_EVENTS: SseEventType[] = [
  'bounty.created',
  'bounty.claimed',
  'bounty.submitted',
  'bounty.approved',
  'bounty.rejected',
  'bounty.disputed',
  'karma.updated',
]

interface UseEventsOptions {
  onEvent?: (event: SseEvent) => void
  enabled?: boolean
}

/**
 * Subscribes to the AlgoBounty SSE event stream.
 * Reconnects with exponential backoff on connection loss.
 */
export function useEvents({ onEvent, enabled = true }: UseEventsOptions = {}) {
  const callbackRef = useRef(onEvent)
  const esRef = useRef<EventSource | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryDelay = useRef(1000)

  // Keep callback ref fresh without causing reconnects
  useEffect(() => {
    callbackRef.current = onEvent
  }, [onEvent])

  const connect = useCallback(() => {
    if (!enabled) return
    if (typeof window === 'undefined') return

    const es = new EventSource(`${API_BASE}/api/v1/events`)
    esRef.current = es

    for (const eventType of SSE_EVENTS) {
      es.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data as string)
          callbackRef.current?.({ type: eventType, data })
          retryDelay.current = 1000 // reset backoff on success
        } catch {
          // ignore malformed events
        }
      })
    }

    es.onerror = () => {
      es.close()
      esRef.current = null
      // Exponential backoff: 1s → 2s → 4s → 8s → max 30s
      const delay = Math.min(retryDelay.current, 30_000)
      retryDelay.current = delay * 2
      retryRef.current = setTimeout(connect, delay)
    }
  }, [enabled])

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
      esRef.current = null
      if (retryRef.current) clearTimeout(retryRef.current)
    }
  }, [connect])
}
