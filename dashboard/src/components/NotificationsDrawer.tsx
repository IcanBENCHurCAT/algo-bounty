'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { NotificationItem } from '@/types'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { useEvents } from '@/hooks/useEvents'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function getIconForMessage(msg: string): string {
  const lower = msg.toLowerCase()
  if (lower.includes('claimed')) return '🤝'
  if (lower.includes('submitted')) return '📬'
  if (lower.includes('approved')) return '✅'
  if (lower.includes('rejected')) return '❌'
  if (lower.includes('dispute')) return '⚖️'
  if (lower.includes('karma')) return '⭐'
  if (lower.includes('bounty')) return '🎯'
  return '📢'
}

interface NotificationsDrawerProps {
  open: boolean
  onClose: () => void
}

export function NotificationsDrawer({ open, onClose }: NotificationsDrawerProps) {
  const { jwt, connected } = useAuth()
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)
  const drawerRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!open) return

    const dialog = drawerRef.current
    if (!dialog) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    dialog.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab') return

      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) {
        event.preventDefault()
        dialog.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (!dialog.contains(active)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
        return
      }

      if (event.shiftKey && (active === first || active === dialog)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      if (previousFocusRef.current?.isConnected) {
        previousFocusRef.current.focus()
      }
    }
  }, [open])

  const unreadCount = notifications.filter((n) => !n.read).length
  const loading = open && connected && Boolean(jwt) && !hasLoaded

  const fetchNotifications = useCallback(async () => {
    if (!jwt) return
    try {
      const items = await getNotifications(jwt)
      setNotifications(items)
    } catch {
      // silently ignore
    } finally {
      setHasLoaded(true)
    }
  }, [jwt])

  useEffect(() => {
    if (!open || !connected || !jwt) return
    let cancelled = false
    getNotifications(jwt)
      .then((items) => {
        if (!cancelled) setNotifications(items)
      })
      .catch(() => {
        // silently ignore
      })
      .finally(() => {
        if (!cancelled) setHasLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [open, connected, jwt])

  useEvents({
    enabled: open && connected,
    onEvent: () => void fetchNotifications()
  })

  const handleMarkRead = async (id: number) => {
    if (!jwt) return
    try {
      await markNotificationRead(id, jwt)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      )
    } catch {
      // keep notification unread if request fails
    }
  }

  const handleMarkAllRead = async () => {
    if (!jwt) return
    try {
      await markAllNotificationsRead(jwt)
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    } catch {
      // keep existing read state if request fails
    }
  }

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          aria-hidden="true"
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            backdropFilter: 'blur(4px)',
            zIndex: 100,
          }}
        />
      )}

      {/* Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="notifications-drawer-title"
        aria-hidden={!open}
        tabIndex={-1}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 'min(400px, 100vw)',
          background: 'rgba(8,8,18,0.98)',
          backdropFilter: 'blur(24px)',
          borderLeft: '1px solid rgba(255,255,255,0.08)',
          zIndex: 101,
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          visibility: open ? 'visible' : 'hidden',
          pointerEvents: open ? 'auto' : 'none',
          transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
          display: 'flex',
          flexDirection: 'column',
          outline: 'none',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2
              id="notifications-drawer-title"
              style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700, color: '#f1f5f9' }}
            >
              Notifications
            </h2>
            {unreadCount > 0 && (
              <span
                style={{
                  padding: '0.125rem 0.5rem',
                  borderRadius: '9999px',
                  background: 'rgba(99,102,241,0.2)',
                  color: '#818cf8',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {unreadCount}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {unreadCount > 0 && (
              <Button variant="ghost" size="sm" onClick={() => void handleMarkAllRead()}>
                Mark all read
              </Button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close notifications"
              className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
              style={{
                background: 'none',
                border: 'none',
                borderRadius: '0.375rem',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '1.25rem',
                padding: '0.375rem 0.5rem',
                lineHeight: 1,
              }}
            >
              <span aria-hidden="true">×</span>
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
              <Spinner />
            </div>
          )}

          {!loading && notifications.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                padding: '3rem 1rem',
                color: '#475569',
                fontSize: '0.9375rem',
              }}
            >
              <div aria-hidden="true" style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔔</div>
              No notifications yet
            </div>
          )}

          {notifications.map((n) => {
            const rowStyle: React.CSSProperties = {
              display: 'flex',
              gap: '0.875rem',
              padding: '0.875rem 1rem',
              borderRadius: '0.75rem',
              marginBottom: '0.375rem',
              background: n.read ? 'transparent' : 'rgba(99,102,241,0.06)',
              border: n.read ? '1px solid transparent' : '1px solid rgba(99,102,241,0.12)',
              cursor: n.read ? 'default' : 'pointer',
              transition: 'background 0.15s',
              width: '100%',
              textAlign: 'left',
            }

            const rowContent = (
              <>
                <span
                  aria-hidden="true"
                  style={{ fontSize: '1.25rem', flexShrink: 0, marginTop: '0.125rem' }}
                >
                  {getIconForMessage(n.message)}
                </span>
                <span style={{ display: 'block', flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      display: 'block',
                      fontSize: '0.875rem',
                      color: '#cbd5e1',
                      marginBottom: '0.25rem',
                      fontWeight: n.read ? 400 : 600,
                    }}
                  >
                    {n.message}
                  </span>
                  <span
                    style={{
                      display: 'block',
                      fontSize: '0.6875rem',
                      color: '#64748b',
                      marginTop: '0.375rem',
                    }}
                  >
                    {timeAgo(n.created_at)}
                  </span>
                </span>
                {!n.read && (
                  <span
                    aria-hidden="true"
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#6366f1',
                      flexShrink: 0,
                      marginTop: '0.375rem',
                    }}
                  />
                )}
              </>
            )

            return n.read ? (
              <div key={n.id} style={rowStyle}>
                {rowContent}
              </div>
            ) : (
              <button
                key={n.id}
                type="button"
                onClick={() => void handleMarkRead(n.id)}
                style={rowStyle}
              >
                <span className="sr-only">Mark notification as read: </span>
                {rowContent}
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}
